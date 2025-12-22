"""
标注缓存服务

职责:
- 缓存键生成
- 结果缓存和获取
- 缓存数据管理
"""

import json
import hashlib
from typing import Dict, Any, Optional, TYPE_CHECKING

from app.core.log_utils import get_logger

if TYPE_CHECKING:
    from app.core.cache.redis import RedisClient

logger = get_logger(__name__)


class CacheService:
    """标注缓存服务"""

    def __init__(self, redis_client: Optional['RedisClient'] = None):
        """
        初始化缓存服务

        Args:
            redis_client: Redis客户端实例（通常是 app.core.redis.RedisClient）
        """
        self.redis_client = redis_client

    def set_redis_client(self, redis_client: 'RedisClient'):
        """设置Redis客户端"""
        self.redis_client = redis_client

    def generate_cache_key(self, slide: Dict[str, Any]) -> str:
        """
        生成缓存键

        Args:
            slide: 幻灯片数据

        Returns:
            str: 缓存键
        """
        screenshot = slide.get("screenshot", "")
        elements_str = json.dumps(slide.get("elements", []), sort_keys=True)
        content = screenshot + elements_str
        return f"annotation:cache:{hashlib.md5(content.encode()).hexdigest()}"

    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存结果

        Args:
            cache_key: 缓存键

        Returns:
            Optional[Dict[str, Any]]: 缓存结果或None
        """
        if not self.redis_client:
            logger.warning("Redis客户端未配置，跳过缓存查询")
            return None

        try:
            cached_str = await self.redis_client.get(cache_key)
            if cached_str:
                return json.loads(cached_str)
        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}", extra={'cache_key': cache_key})

        return None

    async def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """
        缓存结果

        Args:
            cache_key: 缓存键
            result: 结果数据
        """
        if not self.redis_client:
            logger.warning("Redis客户端未配置，跳过缓存存储")
            return

        try:
            await self.redis_client.set(
                cache_key,
                json.dumps(result),
                expire=86400  # 24小时
            )
        except Exception as e:
            logger.error(f"存储缓存失败: {str(e)}", extra={'cache_key': cache_key})
