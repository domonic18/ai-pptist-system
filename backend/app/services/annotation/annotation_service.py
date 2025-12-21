"""
标注服务

职责:
- 实现核心业务逻辑
- 协调各个子服务
- 管理标注任务生命周期
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.repositories.annotation import AnnotationRepository
from app.services.annotation.task_manager import TaskManager
from app.services.annotation.cache_service import CacheService
from app.services.annotation.analysis_service import AnalysisService

logger = get_logger(__name__)


class AnnotationService:
    """标注服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.annotation_repo = AnnotationRepository(db)
        self.redis_client = None  # 延迟初始化
        self.task_manager = TaskManager()
        self.cache_service = CacheService()
        self.analysis_service = AnalysisService(db)

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

        # 初始化Redis客户端
        redis_client = await self._get_redis_client()
        self.task_manager.set_redis_client(redis_client)
        self.cache_service.set_redis_client(redis_client)

        # 创建任务记录
        await self.task_manager.create_task(
            task_id=task_id,
            user_id=user_id,
            slide_count=len(slides),
            model_config=model_config.model_dump() if model_config else None,
            extraction_config=extraction_config.model_dump() if extraction_config else None
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
        user_id: Optional[str]  # noqa: F841 - 可能在未来使用
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
            await self.task_manager.update_task_status(task_id, "processing")

            results = []

            for i, slide in enumerate(slides):
                try:
                    # 更新进度
                    await self.task_manager.update_task_progress(task_id, i, len(slides))

                    # 分析单个幻灯片
                    result = await self.analysis_service.analyze_slide(
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
            await self.task_manager.save_results(task_id, results)

            # 更新任务状态为完成
            await self.task_manager.update_task_status(task_id, "completed")

            logger.info(
                f"标注任务完成: task_id={task_id}, total={len(slides)}, "
                f"success={len([r for r in results if r.get('status') != 'failed'])}"
            )

        except Exception as e:
            logger.error(
                f"标注任务失败: task_id={task_id}",
                exception=e
            )
            await self.task_manager.update_task_status(task_id, "error")


    async def _get_redis_client(self) -> Any:
        """获取Redis客户端（延迟初始化）"""
        if self.redis_client is None:
            from app.core.redis import get_redis
            self.redis_client = await get_redis()
        return self.redis_client