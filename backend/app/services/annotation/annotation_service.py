"""
标注服务

职责:
- 实现核心业务逻辑
- 协调各个子服务
- 管理标注任务生命周期
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.models import ModelManager
from app.core.llm.multimodal.client import MultimodalClient
from app.core.log_utils import get_logger
from app.core.redis import get_redis
from app.prompts import get_prompt_manager, PromptHelper
from app.repositories.annotation import AnnotationRepository

logger = get_logger(__name__)


class AnnotationService:
    """标注服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.annotation_repo = AnnotationRepository(db)
        self.redis_client = None  # 延迟初始化
        self.model_manager = ModelManager()
        self.multimodal_client = MultimodalClient()
        self.prompt_manager = get_prompt_manager()
        self.prompt_helper = PromptHelper(self.prompt_manager)

    async def start_annotation(
        self,
        slides: List[Dict[str, Any]],
        model_config: Optional[Dict[str, Any]] = None,
        extraction_config: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        启动标注任务

        Args:
            slides: 幻灯片数据列表
            model_config: 模型配置
            extraction_config: 提取配置
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 任务信息
        """
        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # 创建任务记录
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "pending",
            "total_pages": len(slides),
            "completed_pages": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_config": model_config.model_dump() if model_config else None,
            "extraction_config": extraction_config.model_dump() if extraction_config else None
        }

        # 保存到Redis
        redis_client = await self._get_redis_client()
        await redis_client.set(
            f"annotation:task:{task_id}",
            json.dumps(task_data),
            expire=3600  # 1小时过期
        )

        # 启动异步标注任务
        asyncio.create_task(
            self._process_annotation_task(task_id, slides, model_config, user_id)
        )

        return {
            "task_id": task_id,
            "estimated_time": len(slides) * 30,  # 每页约30秒
            "total_pages": len(slides)
        }

    async def _process_annotation_task(
        self,
        task_id: str,
        slides: List[Dict[str, Any]],
        model_config: Optional[Dict[str, Any]],
        user_id: Optional[str]
    ):
        """
        处理标注任务（异步执行）

        Args:
            task_id: 任务ID
            slides: 幻灯片数据
            model_config: 模型配置
            user_id: 用户ID
        """
        try:
            # 更新任务状态
            await self._update_task_status(task_id, "processing")

            results = []

            for i, slide in enumerate(slides):
                try:
                    # 更新进度
                    await self._update_task_progress(task_id, i, len(slides))

                    # 分析单个幻灯片
                    result = await self._analyze_slide(
                        slide,
                        model_config
                    )

                    results.append(result)

                except Exception as e:
                    logger.error(
                        f"标注失败: slide_id={slide.get('slide_id')}",
                        exception=e
                    )
                    # 记录失败但继续处理其他页面
                    results.append({
                        "slide_id": slide.get("slide_id"),
                        "status": "failed",
                        "error": str(e)
                    })

            # 保存结果
            await self._save_results(task_id, results)

            # 更新任务状态为完成
            await self._update_task_status(task_id, "completed")

            logger.info(
                f"标注任务完成: task_id={task_id}, total={len(slides)}, "
                f"success={len([r for r in results if r.get('status') != 'failed'])}"
            )

        except Exception as e:
            logger.error(
                f"标注任务失败: task_id={task_id}",
                exception=e
            )
            await self._update_task_status(task_id, "error")

    async def _analyze_slide(
        self,
        slide: Dict[str, Any],
        model_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析单个幻灯片

        Args:
            slide: 幻灯片数据
            model_config: 模型配置

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 1. 检查缓存
        cache_key = self._generate_cache_key(slide)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            logger.info(f"使用缓存结果: slide_id={slide.get('slide_id')}")
            return cached_result

        # 2. 调用多模态分析服务
        try:
            # 获取模型ID，如果没有提供则使用默认的视觉模型
            model_id = model_config.get("model_id") if model_config else None

            if not model_id:
                # 获取默认的视觉模型
                await self.model_manager.ensure_loaded()
                vision_models = [
                    model for model in self.model_manager.text_models + self.model_manager.image_models
                    if getattr(model, 'supports_vision', False) and model.enabled
                ]
                if vision_models:
                    # 优先使用默认模型，否则使用第一个可用的视觉模型
                    default_vision_model = next(
                        (model for model in vision_models if model.is_default),
                        vision_models[0]
                    )
                    model_id = default_vision_model.id
                else:
                    raise ValueError("没有找到可用的视觉模型")

            # 使用提示词模板系统生成分析提示词
            _, user_prompt, temperature, max_tokens = self.prompt_helper.prepare_prompts(
                category="annotation",
                template_name="slide_analysis",
                user_prompt_params={"slide_data": slide}
            )

            # 使用多模态客户端分析图片
            result = await self.multimodal_client.analyze_image(
                image_data=slide.get("screenshot", ""),
                prompt=user_prompt,
                model_config={"model_id": model_id},
                max_tokens=max_tokens,
                temperature=temperature
            )

            # 确保结果包含必要字段
            processed_result = self._process_analysis_result(result, slide)

            # 3. 缓存结果
            await self._cache_result(cache_key, processed_result)

            return processed_result

        except Exception as e:
            logger.error(
                f"幻灯片分析失败: slide_id={slide.get('slide_id')}",
                exception=e
            )
            # 返回失败结果
            return {
                "slide_id": slide.get("slide_id", "unknown"),
                "status": "failed",
                "error": str(e)
            }

    def _process_analysis_result(self, raw_result: Dict[str, Any], slide: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理分析结果，确保格式正确

        Args:
            raw_result: 原始分析结果
            slide: 幻灯片数据

        Returns:
            处理后的分析结果
        """
        slide_id = slide.get("slide_id", "unknown")

        # 如果结果已经是标准格式，直接返回
        if all(key in raw_result for key in ["page_type", "layout_type", "element_annotations"]):
            return {
                "slide_id": slide_id,
                "status": "success",
                **raw_result
            }

        # 如果结果包含analysis字段，尝试解析
        if "analysis" in raw_result:
            analysis_text = raw_result["analysis"]
            try:
                # 尝试从文本中提取JSON
                import re
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group())
                    return {
                        "slide_id": slide_id,
                        "status": "success",
                        **parsed_result
                    }
            except:
                pass

        # 如果无法解析，返回失败结果
        return {
            "slide_id": slide_id,
            "status": "failed",
            "error": "无法解析分析结果"
        }

    async def get_progress(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务进度

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 进度信息
        """
        redis_client = await self._get_redis_client()
        task_data_str = await redis_client.get(f"annotation:task:{task_id}")
        if not task_data_str:
            raise ValueError(f"任务不存在: {task_id}")

        task_data = json.loads(task_data_str)

        return {
            "task_id": task_id,
            "status": task_data.get("status"),
            "progress": {
                "completed": task_data.get("completed_pages", 0),
                "total": task_data.get("total_pages", 0),
                "percentage": int(
                    (task_data.get("completed_pages", 0) / task_data.get("total_pages", 1)) * 100
                )
            },
            "current_page": task_data.get("completed_pages", 0) + 1,
            "estimated_remaining_time": (
                task_data.get("total_pages", 0) - task_data.get("completed_pages", 0)
            ) * 30
        }

    async def get_results(self, task_id: str) -> Dict[str, Any]:
        """
        获取标注结果

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 标注结果
        """
        # 从Redis获取结果
        redis_client = await self._get_redis_client()
        results_str = await redis_client.get(f"annotation:results:{task_id}")
        if not results_str:
            raise ValueError(f"结果不存在: {task_id}")

        results = json.loads(results_str)

        # 计算统计信息
        successful_pages = len([r for r in results if r.get("status") != "failed"])
        failed_pages = len(results) - successful_pages

        total_confidence = sum(
            r.get("overall_confidence", 0)
            for r in results
            if r.get("status") != "failed"
        )
        average_confidence = (
            total_confidence / successful_pages if successful_pages > 0 else 0
        )

        return {
            "task_id": task_id,
            "status": "completed",
            "results": results,
            "statistics": {
                "total_pages": len(results),
                "successful_pages": successful_pages,
                "failed_pages": failed_pages,
                "average_confidence": round(average_confidence, 2)
            }
        }

    async def submit_corrections(
        self,
        task_id: str,
        corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        提交用户修正

        Args:
            task_id: 任务ID
            corrections: 修正数据

        Returns:
            Dict[str, Any]: 修正结果
        """
        # 获取原始结果
        redis_client = await self._get_redis_client()
        results_str = await redis_client.get(f"annotation:results:{task_id}")
        if not results_str:
            raise ValueError(f"结果不存在: {task_id}")

        results = json.loads(results_str)

        # 应用修正
        applied_count = 0
        for correction in corrections:
            slide_id = correction.get("slide_id")
            element_id = correction.get("element_id")

            # 查找对应的结果
            for result in results:
                if result.get("slide_id") == slide_id:
                    # 更新元素标注
                    for elem_ann in result.get("element_annotations", []):
                        if elem_ann.get("element_id") == element_id:
                            elem_ann.update({
                                "type": correction.get("corrected_type"),
                                "confidence": 1.0,  # 用户确认的置信度设为1.0
                                "reason": correction.get("reason", "用户手动修正")
                            })
                            applied_count += 1
                            break
                    break

        # 保存更新后的结果
        await redis_client.set(
            f"annotation:results:{task_id}",
            json.dumps(results),
            expire=3600
        )

        return {
            "applied_corrections": applied_count,
            "updated_results": True
        }

    # 辅助方法
    async def _update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        redis_client = await self._get_redis_client()
        task_data_str = await redis_client.get(f"annotation:task:{task_id}")
        if task_data_str:
            task_data = json.loads(task_data_str)
            task_data["status"] = status
            task_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await redis_client.set(
                f"annotation:task:{task_id}",
                json.dumps(task_data),
                expire=3600
            )

    async def _update_task_progress(
        self,
        task_id: str,
        completed: int,
        total: int
    ):
        """更新任务进度"""
        redis_client = await self._get_redis_client()
        task_data_str = await redis_client.get(f"annotation:task:{task_id}")
        if task_data_str:
            task_data = json.loads(task_data_str)
            task_data["completed_pages"] = completed
            task_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await redis_client.set(
                f"annotation:task:{task_id}",
                json.dumps(task_data),
                expire=3600
            )

    async def _save_results(self, task_id: str, results: List[Dict[str, Any]]):
        """保存标注结果"""
        redis_client = await self._get_redis_client()
        await redis_client.set(
            f"annotation:results:{task_id}",
            json.dumps(results),
            expire=3600
        )

    def _generate_cache_key(self, slide: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        screenshot = slide.get("screenshot", "")
        elements_str = json.dumps(slide.get("elements", []), sort_keys=True)
        content = screenshot + elements_str
        return f"annotation:cache:{hashlib.md5(content.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        redis_client = await self._get_redis_client()
        cached_str = await redis_client.get(cache_key)
        if cached_str:
            return json.loads(cached_str)
        return None

    async def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """缓存结果"""
        redis_client = await self._get_redis_client()
        await redis_client.set(
            cache_key,
            json.dumps(result),
            expire=86400  # 24小时
        )

    async def _get_redis_client(self) -> Any:
        """获取Redis客户端（延迟初始化）"""
        if self.redis_client is None:
            self.redis_client = await get_redis()
        return self.redis_client