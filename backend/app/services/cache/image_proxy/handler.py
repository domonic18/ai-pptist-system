"""
图片代理业务处理器
处理图片代理访问和URL缓存管理的业务逻辑
"""

from typing import Dict, Any, List, Tuple
import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache.url.service import get_image_url_service
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageProxyHandler:
    """图片代理业务处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._service = None

    async def _get_service(self):
        """获取图片URL服务实例"""
        if self._service is None:
            self._service = await get_image_url_service()
        return self._service

    async def handle_get_image_url(
        self,
        image_key: str,
        force_refresh: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        获取图片URL

        Args:
            image_key: 图片键
            force_refresh: 是否强制刷新

        Returns:
            (URL, 元数据) 元组
        """
        service = await self._get_service()
        url, metadata = await service.get_image_url(
            image_key=image_key,
            force_refresh=force_refresh
        )
        return url, metadata

    async def handle_check_url_status(self, image_key: str) -> Dict[str, Any]:
        """
        检查图片URL状态

        Args:
            image_key: 图片键

        Returns:
            状态信息字典
        """
        service = await self._get_service()
        status = await service.check_url_status(image_key)
        return status

    async def handle_refresh_url(
        self,
        image_key: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        刷新图片URL

        Args:
            image_key: 图片键

        Returns:
            (新URL, 元数据) 元组
        """
        service = await self._get_service()
        new_url, metadata = await service.refresh_url(image_key)
        return new_url, metadata

    async def handle_get_multiple_urls(
        self,
        image_keys: List[str],
        force_refresh: bool = False,
        use_cache: bool = True,
        max_concurrent: int = 10
    ) -> Dict[str, Tuple[str, Dict[str, Any]]]:
        """
        批量获取图片URL

        Args:
            image_keys: 图片键列表
            force_refresh: 是否强制刷新
            use_cache: 是否使用缓存
            max_concurrent: 最大并发数

        Returns:
            {image_key: (URL, 元数据)} 字典
        """
        service = await self._get_service()
        results = await service.get_multiple_urls(
            image_keys=image_keys,
            force_refresh=force_refresh,
            use_cache=use_cache,
            max_concurrent=max_concurrent
        )
        return results

    async def handle_get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息

        Returns:
            统计信息字典
        """
        service = await self._get_service()
        stats = await service.get_performance_stats()
        return stats

    async def handle_cleanup_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        service = await self._get_service()
        cleaned = await service.cleanup_expired_cache()
        return cleaned

    async def handle_preload_urls(
        self,
        image_keys: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, bool]:
        """
        预加载图片URL

        Args:
            image_keys: 图片键列表
            max_concurrent: 最大并发数

        Returns:
            {image_key: 是否成功} 字典
        """
        service = await self._get_service()
        results = await service.preload_urls(
            image_keys=image_keys,
            max_concurrent=max_concurrent
        )
        return results
