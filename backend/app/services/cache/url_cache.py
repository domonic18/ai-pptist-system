"""
URL缓存管理模块
负责管理图片URL的缓存、过期和预刷新
"""

import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.log_utils import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    FIFO = "fifo"  # 先进先出


@dataclass
class URLCacheEntry:
    """URL缓存条目"""
    url: str
    expires_at: float  # 过期时间戳（秒）
    access_count: int = 0
    created_at: float = 0
    last_accessed: float = 0
    image_key: str = ""  # COS中的存储键
    mime_type: str = ""  # MIME类型

    def __post_init__(self):
        """初始化后处理"""
        now = time.time()
        if self.created_at == 0:
            self.created_at = now
        if self.last_accessed == 0:
            self.last_accessed = now

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'URLCacheEntry':
        """从字典创建"""
        return cls(**data)

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at

    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_accessed = time.time()


class ImageURLCache:
    """
    图片URL缓存管理器

    功能特性：
    - Redis存储，支持分布式
    - 自动过期检查和清理
    - 智能预刷新机制
    - 访问统计和性能监控
    - 降级处理（缓存失效时直接调用COS）
    """

    # 缓存键前缀
    CACHE_PREFIX = "image:url:"

    # 访问统计键前缀
    STATS_PREFIX = "image:url:stats:"

    # 预刷新队列键前缀
    REFRESH_QUEUE_PREFIX = "image:url:refresh:queue:"

    # 默认配置
    DEFAULT_TTL = 3600  # 默认缓存时间（1小时）
    PRE_REFRESH_THRESHOLD = 900  # 预刷新阈值（15分钟）
    MAX_CACHE_SIZE = 10000  # 最大缓存条目数
    CLEANUP_BATCH_SIZE = 100  # 清理批处理大小

    def __init__(
        self,
        cache_ttl: int = DEFAULT_TTL,
        pre_refresh_threshold: int = PRE_REFRESH_THRESHOLD,
        max_cache_size: int = MAX_CACHE_SIZE,
        strategy: CacheStrategy = CacheStrategy.LRU
    ) -> None:
        """
        初始化URL缓存

        Args:
            cache_ttl: 默认缓存TTL（秒）
            pre_refresh_threshold: 预刷新阈值（秒）
            max_cache_size: 最大缓存大小
            strategy: 缓存淘汰策略
        """
        self.cache_ttl = cache_ttl
        self.pre_refresh_threshold = pre_refresh_threshold
        self.max_cache_size = max_cache_size
        self.strategy = strategy
        self.redis: Optional[object] = None

        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'refreshed': 0,
            'errors': 0
        }

    async def initialize(self) -> None:
        """初始化缓存"""
        self.redis = await get_redis()
        logger.info(
            "URL缓存初始化完成",
            extra={
                'cache_ttl': self.cache_ttl,
                'pre_refresh_threshold': self.pre_refresh_threshold,
                'strategy': self.strategy.value
            }
        )

    def _get_cache_key(self, image_key: str) -> str:
        """获取缓存键"""
        return f"{self.CACHE_PREFIX}{image_key}"

    def _get_stats_key(self, image_key: str) -> str:
        """获取统计键"""
        return f"{self.STATS_PREFIX}{image_key}"

    async def get(self, image_key: str) -> Optional[URLCacheEntry]:
        """
        获取缓存的URL

        Args:
            image_key: 图片在COS中的存储键

        Returns:
            URLCacheEntry: 缓存条目，如果不存在或过期则返回None
        """
        if not self.redis:
            await self.initialize()

        cache_key = self._get_cache_key(image_key)

        try:
            # 从Redis获取缓存
            cached_data = await self.redis.get(cache_key)

            if not cached_data:
                self.stats['misses'] += 1
                logger.debug(f"缓存未命中: {image_key}")
                return None

            # 反序列化数据
            try:
                data = json.loads(cached_data)
                entry = URLCacheEntry.from_dict(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"缓存数据反序列化失败: {str(e)}", extra={'image_key': image_key})
                self.stats['errors'] += 1
                await self.delete(image_key)
                return None

            # 检查是否过期
            if entry.is_expired():
                self.stats['expired'] += 1
                logger.debug(f"缓存已过期: {image_key}")
                await self.delete(image_key)
                return None

            # 记录访问
            entry.access()
            await self._update_cache_entry(cache_key, entry)

            self.stats['hits'] += 1
            logger.debug(f"缓存命中: {image_key}, 访问次数: {entry.access_count}")
            return entry

        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}", extra={'image_key': image_key})
            self.stats['errors'] += 1
            return None

    async def set(
        self,
        image_key: str,
        url: str,
        expires_in: Optional[int] = None,
        mime_type: str = ""
    ) -> bool:
        """
        设置URL缓存

        Args:
            image_key: 图片在COS中的存储键
            url: 预签名URL
            expires_in: 过期时间（秒），使用默认TTL
            mime_type: MIME类型

        Returns:
            bool: 是否设置成功
        """
        if not self.redis:
            await self.initialize()

        cache_key = self._get_cache_key(image_key)
        ttl = expires_in or self.cache_ttl

        try:
            # 创建缓存条目
            entry = URLCacheEntry(
                url=url,
                expires_at=time.time() + ttl,
                image_key=image_key,
                mime_type=mime_type
            )

            # 序列化并存储
            data = entry.to_dict()
            await self.redis.set(cache_key, json.dumps(data, ensure_ascii=False), expire=ttl)

            logger.debug(f"缓存设置成功: {image_key}, TTL: {ttl}秒")
            return True

        except Exception as e:
            logger.error(f"设置缓存失败: {str(e)}", extra={'image_key': image_key, 'url': url})
            self.stats['errors'] += 1
            return False

    async def delete(self, image_key: str) -> bool:
        """
        删除缓存

        Args:
            image_key: 图片在COS中的存储键

        Returns:
            bool: 是否删除成功
        """
        if not self.redis:
            await self.initialize()

        cache_key = self._get_cache_key(image_key)

        try:
            await self.redis.delete(cache_key)
            logger.debug(f"缓存删除成功: {image_key}")
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}", extra={'image_key': image_key})
            self.stats['errors'] += 1
            return False

    async def refresh(self, image_key: str) -> Optional[URLCacheEntry]:
        """
        刷新缓存（预刷新机制）

        Args:
            image_key: 图片在COS中的存储键

        Returns:
            URLCacheEntry: 刷新后的缓存条目
        """
        logger.info(f"开始预刷新缓存: {image_key}")

        # 移除旧的缓存
        await self.delete(image_key)

        # 重新生成URL（需要调用方提供生成逻辑）
        # 这里先标记需要刷新，实际生成由上层服务处理
        self.stats['refreshed'] += 1

        return None

    async def is_near_expiry(self, image_key: str, threshold: Optional[int] = None) -> bool:
        """
        检查缓存是否即将过期

        Args:
            image_key: 图片在COS中的存储键
            threshold: 过期阈值（秒），使用默认阈值

        Returns:
            bool: 是否即将过期
        """
        if not self.redis:
            await self.initialize()

        entry = await self.get(image_key)
        if not entry:
            return False

        threshold = threshold or self.pre_refresh_threshold
        time_until_expiry = entry.expires_at - time.time()

        return time_until_expiry <= threshold

    async def cleanup_expired(self) -> int:
        """
        清理过期的缓存

        Returns:
            int: 清理的缓存数量
        """
        if not self.redis:
            await self.initialize()

        cleaned = 0
        try:
            # 扫描所有缓存键
            pattern = f"{self.CACHE_PREFIX}*"
            keys = await self.redis._client.keys(pattern)

            batch = []
            for key in keys:
                try:
                    # 获取并检查过期时间
                    cached_data = await self.redis.get(key)
                    if cached_data:
                        data = json.loads(cached_data)
                        entry = URLCacheEntry.from_dict(data)
                        if entry.is_expired():
                            batch.append(key)
                except Exception:
                    # 解析失败，删除该键
                    batch.append(key)

                # 批量清理
                if len(batch) >= self.CLEANUP_BATCH_SIZE:
                    if batch:
                        await self.redis.delete(*batch)
                        cleaned += len(batch)
                        batch = []

            # 清理剩余的
            if batch:
                await self.redis.delete(*batch)
                cleaned += len(batch)

            logger.info(f"清理过期缓存完成: {cleaned}个")
            return cleaned

        except Exception as e:
            logger.error(f"清理过期缓存失败: {str(e)}")
            self.stats['errors'] += 1
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.redis:
            await self.initialize()

        try:
            # 获取缓存键数量
            pattern = f"{self.CACHE_PREFIX}*"
            keys = await self.redis._client.keys(pattern)
            total_keys = len(keys)

            # 计算命中率
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                'total_keys': total_keys,
                'hit_rate': round(hit_rate, 2),
                'stats': self.stats.copy(),
                'config': {
                    'cache_ttl': self.cache_ttl,
                    'pre_refresh_threshold': self.pre_refresh_threshold,
                    'max_cache_size': self.max_cache_size,
                    'strategy': self.strategy.value
                }
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {'error': str(e)}

    async def _update_cache_entry(self, cache_key: str, entry: URLCacheEntry):
        """
        更新缓存条目（只更新访问次数）

        Args:
            cache_key: 缓存键
            entry: 缓存条目
        """
        try:
            data = entry.to_dict()
            # 计算剩余TTL
            ttl = int(entry.expires_at - time.time())
            if ttl > 0:
                await self.redis.set(cache_key, json.dumps(data, ensure_ascii=False), expire=ttl)
        except Exception as e:
            logger.error(f"更新缓存条目失败: {str(e)}", extra={'cache_key': cache_key})

    async def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 是否清空成功
        """
        if not self.redis:
            await self.initialize()

        try:
            pattern = f"{self.CACHE_PREFIX}*"
            keys = await self.redis._client.keys(pattern)

            if keys:
                await self.redis.delete(*keys)

            # 重置统计
            self.stats = {
                'hits': 0,
                'misses': 0,
                'expired': 0,
                'refreshed': 0,
                'errors': 0
            }

            logger.info(f"清空所有缓存完成: {len(keys)}个键")
            return True

        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            self.stats['errors'] += 1
            return False


# 全局URL缓存实例
url_cache = ImageURLCache()


async def get_url_cache() -> ImageURLCache:
    """获取URL缓存实例"""
    if not url_cache.redis:
        await url_cache.initialize()
    return url_cache
