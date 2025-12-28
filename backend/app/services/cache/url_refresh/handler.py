"""
URL缓存刷新处理器
处理URL刷新相关的业务逻辑
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks import (
    refresh_url_cache,
    batch_refresh_url_cache,
    schedule_periodic_refresh,
)
from app.schemas.url_cache_refresh import (
    UrlRefreshRequest,
    BatchUrlRefreshRequest,
    ScheduleRefreshRequest,
    UrlRefreshResponse,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class UrlRefreshHandler:
    """URL缓存刷新处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_refresh_single_url(
        self,
        request: UrlRefreshRequest
    ) -> Dict[str, Any]:
        """
        处理单个URL刷新

        Args:
            request: URL刷新请求

        Returns:
            包含task_id的字典
        """
        logger.info(
            "处理单个URL刷新请求",
            extra={
                'image_key': request.image_key,
                'force_refresh': request.force_refresh
            }
        )

        task = refresh_url_cache.apply_async(
            args=[request.image_key],
            kwargs={"force_refresh": request.force_refresh}
        )

        logger.info(
            "URL刷新任务已创建",
            extra={'task_id': task.id, 'image_key': request.image_key}
        )

        return {
            "task_id": task.id,
            "status": "PENDING"
        }

    async def handle_batch_refresh_urls(
        self,
        request: BatchUrlRefreshRequest
    ) -> Dict[str, Any]:
        """
        处理批量URL刷新

        Args:
            request: 批量刷新请求

        Returns:
            包含task_id的字典
        """
        logger.info(
            "处理批量URL刷新请求",
            extra={
                'count': len(request.image_keys),
                'batch_size': request.batch_size
            }
        )

        task = batch_refresh_url_cache.apply_async(
            args=[request.image_keys],
            kwargs={"batch_size": request.batch_size}
        )

        logger.info(
            "批量URL刷新任务已创建",
            extra={'task_id': task.id, 'count': len(request.image_keys)}
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "count": len(request.image_keys)
        }

    async def handle_schedule_periodic_refresh(
        self,
        request: ScheduleRefreshRequest
    ) -> Dict[str, Any]:
        """
        处理定期刷新调度

        Args:
            request: 定期刷新请求

        Returns:
            包含task_id的字典
        """
        logger.info(
            "处理定期刷新调度请求",
            extra={
                'image_key': request.image_key,
                'refresh_interval': request.refresh_interval
            }
        )

        task_id = schedule_periodic_refresh(
            request.image_key,
            request.refresh_interval
        )

        logger.info(
            "定期刷新任务已调度",
            extra={'task_id': task_id, 'image_key': request.image_key}
        )

        return {
            "task_id": task_id,
            "status": "SCHEDULED",
            "refresh_interval": request.refresh_interval
        }
