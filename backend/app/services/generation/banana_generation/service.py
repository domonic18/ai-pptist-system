"""
Banana生成服务（Facade层）
整合所有生成任务相关的服务，对外提供统一的接口
"""

import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation.banana_generation.slide_generator import BananaSlideGenerator
from app.services.generation.banana_generation.task_manager import BananaTaskManager
from app.services.tasks.banana_generation_tasks import (
    generate_batch_slides_task,
    generate_single_slide_task,
)
from app.repositories.banana_generation import BananaGenerationRepository
from app.core.cache.redis import get_redis
from app.core.log_utils import get_logger
from app.models.banana_generation_task import TaskStatus
from datetime import datetime

from app.prompts import get_prompt_manager
from app.prompts import PromptHelper
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.repositories.ai_model import AIModelRepository
from app.core.config.config import settings

logger = get_logger(__name__)


class BananaGenerationService:
    """Banana生成服务（门面模式）"""

    def __init__(self, db: AsyncSession):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repo = BananaGenerationRepository(db)
        self.slide_generator = BananaSlideGenerator()
        self.task_manager = None  # 延迟初始化，需要异步
        self.prompt_manager = get_prompt_manager()
        self.prompt_helper = PromptHelper(self.prompt_manager)

    async def split_outline(
        self,
        content: str,
        ai_model_id: str
    ) -> Dict[str, Any]:
        """
        将大纲内容拆分为结构化的PPT页面数据

        Args:
            content: 原始Markdown大纲内容
            ai_model_id: AI模型ID

        Returns:
            Dict: 结构化的幻灯片数据 {title, slides: [{title, points}]}
        """
        logger.info("开始拆分大纲", extra={"ai_model_id": ai_model_id, "content_len": len(content)})

        # ==================== Mock模式 ====================
        if settings.enable_banana_outline_split_mock:
            logger.info("使用Mock模式进行大纲拆分")
            mock_file_path = Path(settings.absolute_mockdata_dir) / "banana_outline_split_example.json"
            try:
                with open(mock_file_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                logger.info("Mock数据读取成功", extra={"slides_count": len(result.get("slides", []))})
                return result
            except FileNotFoundError:
                logger.error(f"Mock文件未找到: {mock_file_path}")
                raise ValueError(f"Mock文件未找到: {mock_file_path}，请检查文件是否存在")
            except json.JSONDecodeError as e:
                logger.error(f"Mock文件JSON解析失败: {e}")
                raise ValueError(f"Mock文件格式错误: {e}")

        # ==================== 正常模式 ====================
        # 1. 获取模型配置
        ai_model_repo = AIModelRepository(self.db)
        ai_model = await ai_model_repo.get_model_by_id(ai_model_id)
        if not ai_model:
            raise ValueError(f"未找到AI模型: {ai_model_id}")
        
        # 构建标准模型配置字典（与项目中其他 Service 保持一致）
        model_config = {
            'id': ai_model.id,
            'ai_model_name': ai_model.ai_model_name,
            'base_url': ai_model.base_url,
            'api_key': ai_model.api_key,
            'capabilities': ai_model.capabilities,
            'provider_mapping': ai_model.provider_mapping,
            'max_tokens': ai_model.max_tokens,
            'context_window': ai_model.context_window,
            'parameters': ai_model.parameters or {}
        }
        
        # 2. 准备提示词
        system_prompt, user_prompt, temperature, max_tokens = \
            self.prompt_helper.prepare_prompts(
                "presentation",
                "banana_outline_split",
                {"content": content},
                {}
            )
            
        # 3. 调用AI模型
        provider_mapping = ai_model.provider_mapping or {}
        provider_name = provider_mapping.get('chat', 'openai_compatible')
        
        chat_provider = AIProviderFactory.create_provider(
            capability=ModelCapability.CHAT,
            provider_name=provider_name,
            model_config=model_config
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # 非流式调用
            response = await chat_provider.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # 解析结果
            # response 为字典，需提取 content 字段
            raw_content = response.get("content", "")
            
            # 有些模型可能会返回带有markdown代码块的结果，需要清理
            content = raw_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            logger.info("大纲拆分成功", extra={"slides_count": len(result.get("slides", []))})
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析大纲拆分结果失败: {e}", extra={"content": response})
            raise ValueError("AI返回了大纲拆分结果，但格式解析失败，请重试")
        except Exception as e:
            logger.error(f"大纲拆分失败: {e}")
            raise e
        finally:
            if hasattr(chat_provider, 'close'):
                await chat_provider.close()

    async def generate_batch_slides(
        self,
        outline: Dict[str, Any],
        template_id: Optional[str],
        generation_model: str,
        canvas_size: Dict[str, float],
        user_id: Optional[str] = None,
        custom_template_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量生成幻灯片图片

        Args:
            outline: PPT大纲数据
            template_id: 模板ID（与custom_template_url二选一）
            generation_model: 生成模型名称
            canvas_size: 画布尺寸
            user_id: 用户ID（可选）
            custom_template_url: 自定义模板图片URL（与template_id二选一）

        Returns:
            Dict: 包含task_id等信息
        """
        task_id = f"banana_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 1. 创建任务记录
        # 准备幻灯片数据
        slides = outline.get("slides", [])
        total_slides = len(slides)

        if total_slides == 0:
            raise ValueError("大纲中没有幻灯片数据")

        # 获取模板图片URL：优先使用自定义URL，否则从数据库获取
        template_image_url = None

        if custom_template_url:
            # 使用用户上传的自定义模板URL
            template_image_url = custom_template_url
            logger.info("使用自定义模板URL", extra={
                "custom_template_url": custom_template_url[:100]
            })
        elif template_id:
            # 从数据库获取模板信息（模板图片存储在 COS）
            template = await self.repo.get_template(template_id)
            if not template:
                raise ValueError(
                    f"模板未找到: {template_id}。"
                    f"请先运行初始化脚本将模板上传到 COS: "
                    f"python -m scripts.init_banana_templates"
                )
            # 使用 COS 中的模板图片 URL
            template_image_url = template.full_image_url
            logger.info("获取模板信息", extra={
                "template_id": template_id,
                "template_image_url": template_image_url
            })
        else:
            raise ValueError("template_id和custom_template_url必须提供其中一个")

        task = await self.repo.create_task(
            task_id=task_id,
            outline=outline,
            template_id=template_id,
            template_image_url=template_image_url,
            generation_model=generation_model,
            canvas_size=canvas_size,
            total_slides=total_slides,
            user_id=user_id
        )

        # 增加模板使用次数（仅对系统模板）
        if template_id:
            await self.repo.increment_template_usage(template_id)

        # 格式化幻灯片数据
        formatted_slides = []
        for idx, slide in enumerate(slides):
            formatted_slide = {
                "title": slide.get("title", ""),
                "points": slide.get("points", []),
                "ppt_title": outline.get("title", "PPT演示"),
                "total_pages": total_slides,
                "index": idx
            }
            formatted_slides.append(formatted_slide)

        # 提交Celery任务
        celery_result = generate_batch_slides_task.apply_async(
            kwargs={
                "task_id": task_id,
                "slides": formatted_slides,
                "template_image_url": template_image_url,
                "generation_model": generation_model,
                "canvas_size": canvas_size
            },
            queue="banana"
        )

        # 更新任务with Celery信息
        await self.repo.update_task_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            celery_task_id=celery_result.id
        )

        # 将任务信息保存到Redis，供Celery worker使用
        redis_client = await get_redis()
        task_info_key = f"banana:task:{task_id}:info"
        task_info = {
            "task_id": task_id,
            "total_slides": total_slides,
            "template_id": template_id,
            "generation_model": generation_model,
            "canvas_size": canvas_size,
            "created_at": datetime.utcnow().isoformat()
        }
        await redis_client.set(
            task_info_key,
            json.dumps(task_info),
            expire=3600
        )

        logger.info("批量生成任务已提交", extra={
            "task_id": task_id,
            "total_slides": total_slides,
            "template_id": template_id
        })

        return {
            "task_id": task_id,
            "celery_task_id": celery_result.id,
            "total_slides": total_slides,
            "status": "processing"
        }

    async def get_generation_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取生成任务状态（前端轮询）

        Args:
            task_id: 任务ID

        Returns:
            Dict: 包含进度和每个幻灯片的状态
        """
        if not self.task_manager:
            redis_client = await get_redis()
            self.task_manager = BananaTaskManager(redis_client)

        progress_data = await self.task_manager.get_task_progress(task_id)

        # 检查Redis数据是否有效（新格式：progress嵌套）
        progress_total = 0
        if progress_data and "progress" in progress_data:
            progress_total = progress_data.get("progress", {}).get("total", 0)
        
        if progress_data is None or progress_total == 0:
            # 从数据库获取任务信息
            task = await self.repo.get_task(task_id)

            if not task:
                return {
                    "task_id": task_id,
                    "status": "not_found",
                    "progress": {
                        "total": 0,
                        "completed": 0,
                        "failed": 0,
                        "pending": 0
                    },
                    "slides": []
                }

            progress_data = {
                "task_id": task_id,
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "progress": {
                    "total": task.total_slides,
                    "completed": task.completed_slides,
                    "failed": task.failed_slides,
                    "pending": max(0, task.total_slides - task.completed_slides - task.failed_slides)
                },
                "slides": []
            }

        return progress_data

    async def stop_generation(self, task_id: str) -> Dict[str, Any]:
        """
        停止生成任务

        Args:
            task_id: 任务ID

        Returns:
            Dict: 停止结果
        """
        task = await self.repo.get_task(task_id)

        if not task:
            raise ValueError(f"任务未找到: {task_id}")

        # 更新任务状态为取消
        await self.repo.update_task_status(
            task_id=task_id,
            status=TaskStatus.CANCELLED
        )

        completed_slides = task.completed_slides
        total_slides = task.total_slides
        celery_group_id = task.celery_group_id

        # 如果有Celery任务ID，尝试取消
        if celery_group_id:
            try:
                from celery import Celery
                celery = Celery()
                celery.control.revoke(celery_group_id, terminate=True)
            except Exception as e:
                logger.warning(f"取消Celery任务失败: {e}")

        logger.info("停止Banana生成任务", extra={
            "task_id": task_id,
            "celery_group_id": celery_group_id
        })

        return {
            "task_id": task_id,
            "status": "stopped",
            "completed_slides": completed_slides,
            "total_slides": total_slides
        }

    async def regenerate_slide(
        self,
        task_id: str,
        slide_index: int
    ) -> Dict[str, Any]:
        """
        重新生成单张幻灯片

        Args:
            task_id: 任务ID
            slide_index: 幻灯片索引

        Returns:
            Dict: 重新生成结果
        """
        task = await self.repo.get_task(task_id)

        if not task:
            raise ValueError(f"任务未找到: {task_id}")

        if slide_index < 0 or slide_index >= task.total_slides:
            raise ValueError(f"错误的幻灯片索引: {slide_index}")

        # 获取幻灯片数据
        outline = task.outline
        slides = outline.get('slides', [])

        if slide_index >= len(slides):
            raise ValueError(f"幻灯片索引超出范围: {slide_index}")

        slide_data = slides[slide_index]
        slide_data.update({
            'ppt_title': outline.get('title', 'PPT演示'),
            'total_pages': task.total_slides
        })

        template_image_url = task.template_image_url
        generation_model = task.generation_model
        canvas_size = task.canvas_size

        # 提交单个幻灯片生成任务
        result = generate_single_slide_task.apply_async(
            kwargs={
                "task_id": task_id,
                "slide_index": slide_index,
                "slide_data": slide_data,
                "template_image_url": template_image_url,
                "generation_model": generation_model,
                "canvas_size": canvas_size
            },
            queue="banana"
        )

        logger.info("重新生成幻灯片任务已提交", extra={
            "task_id": task_id,
            "slide_index": slide_index
        })

        return {
            "slide_index": slide_index,
            "status": "processing",
            "celery_task_id": result.id
        }

    async def get_templates(
        self,
        template_type: Optional[str] = None,
        aspect_ratio: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取可用模板列表

        Args:
            template_type: 模板类型（system|user）
            aspect_ratio: 宽高比（16:9|4:3）

        Returns:
            Dict: 模板列表
        """
        from app.services.cache.url.service import get_image_url_service
        url_service = await get_image_url_service()
        
        templates = await self.repo.get_templates(template_type=template_type, aspect_ratio=aspect_ratio)

        formatted_templates = []
        for t in templates:
            # 为私有 COS 路径生成预签名 URL
            # 兼容处理：Key, 带前导斜杠的 Key, 以及不带签名的全路径 URL
            async def get_signed_url(url_or_key: str) -> str:
                if not url_or_key:
                    return url_or_key
                
                is_http = url_or_key.startswith(('http://', 'https://'))
                is_cos_url = 'myqcloud.com' in url_or_key
                has_signature = 'q-signature' in url_or_key
                
                if not is_http or (is_cos_url and not has_signature):
                    try:
                        cos_key = url_or_key
                        if is_http:
                            from urllib.parse import urlparse
                            cos_key = urlparse(url_or_key).path.lstrip('/')
                        else:
                            cos_key = url_or_key.lstrip('/')
                        
                        url, _ = await url_service.get_image_url(cos_key)
                        return url
                    except Exception as e:
                        logger.warning(f"生成预签名 URL 失败 ({url_or_key}): {e}")
                return url_or_key

            cover_url = await get_signed_url(t.cover_url)
            full_image_url = await get_signed_url(t.full_image_url)

            formatted_templates.append({
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "cover_url": cover_url,
                "full_image_url": full_image_url,
                "type": t.type,
                "aspect_ratio": t.aspect_ratio,
                "usage_count": t.usage_count,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })

        return {
            "templates": formatted_templates
        }
