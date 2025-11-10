"""
图片URL管理服务
集成Redis缓存和COS存储，提供智能URL管理功能
"""

import asyncio
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.core.log_utils import get_logger
from app.core.storage.cos_storage import COSStorage
from app.core.cos import get_cos_config
from .url_cache import ImageURLCache, URLCacheEntry, get_url_cache

logger = get_logger(__name__)


class ImageURLService:
    """
    图片URL管理服务

    核心功能：
    - 智能URL生成和缓存
    - 预签名URL生命周期管理
    - 自动预刷新和降级处理
    - 访问统计和性能监控
    """

    def __init__(self, cos_storage: Optional[COSStorage] = None):
        """
        初始化服务

        Args:
            cos_storage: COS存储实例，如果为None则创建新实例
        """
        self.cos_storage = cos_storage or COSStorage()
        self.url_cache: Optional[ImageURLCache] = None
        self.cos_config = get_cos_config()

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cos_calls': 0,
            'avg_response_time': 0,
            'errors': 0
        }

    async def initialize(self) -> None:
        """初始化服务"""
        self.url_cache = await get_url_cache()
        logger.info("图片URL管理服务初始化完成")

    async def get_image_url(
        self,
        image_key: str,
        force_refresh: bool = False,
        use_cache: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        获取图片访问URL

        这是核心方法，智能判断是否从缓存获取还是重新生成

        Args:
            image_key: 图片在COS中的存储键
            force_refresh: 是否强制刷新
            use_cache: 是否使用缓存

        Returns:
            Tuple[str, Dict[str, Any]]: (URL, 元数据)

        Raises:
            ValueError: 如果image_key无效
        """
        if not image_key:
            raise ValueError("image_key不能为空")

        self.performance_stats['total_requests'] += 1
        start_time = time.time()

        try:
            # 1. 尝试从缓存获取（检查是否过期）
            if use_cache and not force_refresh:
                cached_entry = await self.url_cache.get(image_key)
                if cached_entry and not cached_entry.is_expired():
                    self.performance_stats['cache_hits'] += 1
                    response_time = time.time() - start_time
                    self._update_response_time(response_time)

                    logger.info(
                        f"从缓存获取URL成功: {image_key}",
                        extra={
                            'image_key': image_key,
                            'response_time': response_time,
                            'cache_hit': True,
                            'is_expired': False
                        }
                    )

                    return cached_entry.url, self._build_metadata(cached_entry, from_cache=True)
                elif cached_entry and cached_entry.is_expired():
                    # 缓存存在但已过期，记录日志并继续获取新URL
                    logger.warning(
                        f"缓存命中但已过期: {image_key}，将重新生成URL",
                        extra={
                            'image_key': image_key,
                            'expired_at': cached_entry.expires_at,
                            'current_time': time.time()
                        }
                    )
            # 2. 缓存未命中/过期或强制刷新，调用COS生成新URL
            logger.info(f"缓存未命中，调用COS生成新URL: {image_key}")
            self.performance_stats['cos_calls'] += 1

            # 生成新的预签名URL
            new_url = await self.cos_storage.generate_url(
                key=image_key,
                expires=self.cos_config.url_expires,
                operation="get"
            )

            # 3. 更新缓存
            if use_cache:
                await self.url_cache.set(
                    image_key=image_key,
                    url=new_url,
                    expires_in=self.cos_config.url_expires,
                    mime_type="image/jpeg"  # 后续可以从COS获取实际类型
                )

            # 4. 返回URL和元数据
            response_time = time.time() - start_time
            self._update_response_time(response_time)

            metadata = {
                'image_key': image_key,
                'expires_at': time.time() + self.cos_config.url_expires,
                'from_cache': False,
                'response_time': response_time
            }

            logger.info(
                f"从COS生成新URL成功: {image_key}",
                extra={
                    'image_key': image_key,
                    'response_time': response_time,
                    'cache_hit': False
                }
            )

            return new_url, metadata

        except Exception as e:
            self.performance_stats['errors'] += 1
            logger.error(
                f"获取图片URL失败: {str(e)}",
                extra={'image_key': image_key, 'error': str(e)}
            )
            raise

    async def get_multiple_urls(
        self,
        image_keys: list,
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
            Dict[str, Tuple[str, Dict[str, Any]]]: 图片键到(URL, 元数据)的映射
        """
        if not image_keys:
            return {}

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_single_url(key: str) -> Tuple[str, Tuple[str, Dict[str, Any]]]:
            async with semaphore:
                try:
                    url, metadata = await self.get_image_url(key, force_refresh, use_cache)
                    return key, (url, metadata)
                except Exception as e:
                    logger.error(f"批量获取URL失败: {str(e)}", extra={'image_key': key})
                    # 返回错误标记
                    return key, ('', {'error': str(e), 'image_key': key})

        # 并发执行
        tasks = [get_single_url(key) for key in image_keys]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in completed:
            if isinstance(result, tuple) and len(result) == 2:
                key, (url, metadata) = result
                results[key] = (url, metadata)

        logger.info(
            f"批量获取URL完成: {len(results)}/{len(image_keys)}个成功",
            extra={'total': len(image_keys), 'success': len(results)}
        )

        return results

    async def refresh_url(self, image_key: str) -> Tuple[str, Dict[str, Any]]:
        """
        刷新图片URL

        Args:
            image_key: 图片在COS中的存储键

        Returns:
            Tuple[str, Dict[str, Any]]: (新URL, 元数据)
        """
        logger.info(f"开始刷新URL: {image_key}")

        # 1. 删除旧缓存
        await self.url_cache.delete(image_key)

        # 2. 生成新URL
        new_url, metadata = await self.get_image_url(image_key, force_refresh=True)

        # 3. 更新元数据
        metadata['refreshed'] = True
        metadata['refreshed_at'] = time.time()

        logger.info(f"URL刷新成功: {image_key}")
        return new_url, metadata

    async def check_url_status(self, image_key: str) -> Dict[str, Any]:
        """
        检查URL状态

        Args:
            image_key: 图片在COS中的存储键

        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            # 1. 检查缓存中的状态
            cached_entry = await self.url_cache.get(image_key)

            if cached_entry:
                time_until_expiry = cached_entry.expires_at - time.time()
                is_near_expiry = await self.url_cache.is_near_expiry(image_key)

                return {
                    'image_key': image_key,
                    'exists_in_cache': True,
                    'is_expired': cached_entry.is_expired(),
                    'is_near_expiry': is_near_expiry,
                    'time_until_expiry': time_until_expiry,
                    'expires_at': cached_entry.expires_at,
                    'access_count': cached_entry.access_count,
                    'last_accessed': cached_entry.last_accessed,
                    'created_at': cached_entry.created_at,
                    'url': cached_entry.url,
                    'status': 'healthy' if not is_near_expiry else 'near_expiry'
                }
            else:
                # 2. 检查COS中的文件是否存在
                exists = await self.cos_storage.exists(image_key)

                return {
                    'image_key': image_key,
                    'exists_in_cache': False,
                    'exists_in_cos': exists,
                    'status': 'not_cached' if exists else 'not_found'
                }

        except Exception as e:
            logger.error(f"检查URL状态失败: {str(e)}", extra={'image_key': image_key})
            return {
                'image_key': image_key,
                'status': 'error',
                'error': str(e)
            }

    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计

        Returns:
            Dict[str, Any]: 性能统计信息
        """
        # 合并缓存统计
        cache_stats = await self.url_cache.get_stats()

        # 计算缓存命中率
        total_requests = self.performance_stats['total_requests']
        cache_hits = self.performance_stats['cache_hits']
        cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'service_stats': self.performance_stats.copy(),
            'cache_stats': cache_stats,
            'performance': {
                'total_requests': total_requests,
                'cache_hits': cache_hits,
                'cache_hit_rate': round(cache_hit_rate, 2),
                'cos_calls': self.performance_stats['cos_calls'],
                'cos_call_rate': round(
                    (self.performance_stats['cos_calls'] / total_requests * 100)
                    if total_requests > 0 else 0, 2
                ),
                'errors': self.performance_stats['errors'],
                'error_rate': round(
                    (self.performance_stats['errors'] / total_requests * 100)
                    if total_requests > 0 else 0, 2
                ),
                'avg_response_time': round(self.performance_stats['avg_response_time'], 3)
            },
            'timestamp': time.time()
        }

    async def cleanup_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            int: 清理的缓存数量
        """
        cleaned = await self.url_cache.cleanup_expired()
        logger.info(f"清理过期缓存完成: {cleaned}个")
        return cleaned

    async def preload_urls(self, image_keys: list, max_concurrent: int = 5) -> Dict[str, bool]:
        """
        预加载URL到缓存

        Args:
            image_keys: 图片键列表
            max_concurrent: 最大并发数

        Returns:
            Dict[str, bool]: 预加载结果
        """
        if not image_keys:
            return {}

        logger.info(f"开始预加载 {len(image_keys)} 个URL")

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def preload_single(key: str) -> Tuple[str, bool]:
            async with semaphore:
                try:
                    await self.get_image_url(key, use_cache=True)
                    return key, True
                except Exception as e:
                    logger.error(f"预加载URL失败: {str(e)}", extra={'image_key': key})
                    return key, False

        # 并发执行
        tasks = [preload_single(key) for key in image_keys]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for result in completed:
            if isinstance(result, tuple) and len(result) == 2:
                key, success = result
                results[key] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"预加载完成: {success_count}/{len(image_keys)}个成功",
            extra={'total': len(image_keys), 'success': success_count}
        )

        return results

    def _build_metadata(self, entry: URLCacheEntry, from_cache: bool) -> Dict[str, Any]:
        """构建元数据"""
        return {
            'image_key': entry.image_key,
            'expires_at': entry.expires_at,
            'from_cache': from_cache,
            'access_count': entry.access_count,
            'last_accessed': entry.last_accessed,
            'created_at': entry.created_at,
            'mime_type': entry.mime_type
        }

    def _update_response_time(self, response_time: float):
        """更新平均响应时间"""
        # 使用指数移动平均
        current_avg = self.performance_stats['avg_response_time']
        if current_avg == 0:
            self.performance_stats['avg_response_time'] = response_time
        else:
            # EMA系数
            alpha = 0.1
            self.performance_stats['avg_response_time'] = (
                alpha * response_time + (1 - alpha) * current_avg
            )


# 全局服务实例
image_url_service = ImageURLService()


async def get_image_url_service() -> ImageURLService:
    """获取图片URL服务实例"""
    if not image_url_service.url_cache:
        await image_url_service.initialize()
    return image_url_service
