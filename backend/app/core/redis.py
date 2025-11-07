"""
Redis客户端连接管理
统一管理Redis连接，支持连接池和错误处理
"""

import asyncio
import json
import time
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis客户端封装类，提供连接管理和操作封装"""

    def __init__(self):
        self._client = None
        self._connection_pool = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化Redis连接"""
        if self._initialized:
            return

        try:
            # 延迟导入redis-py，避免启动时依赖问题
            import redis.asyncio as redis
            from redis.asyncio.connection import ConnectionPool

            # 创建连接池
            self._connection_pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )

            # 创建客户端
            self._client = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True,
                auto_close_connection_pool=False,
            )

            # 测试连接
            await self._client.ping()
            self._initialized = True

            logger.info(
                "Redis连接初始化成功",
                extra={
                    'host': settings.redis_host,
                    'port': settings.redis_port,
                    'db': settings.redis_db
                }
            )

        except Exception as e:
            logger.error(
                f"Redis连接初始化失败: {str(e)}",
                extra={
                    'redis_url': settings.redis_url,
                    'error_type': type(e).__name__
                }
            )
            raise

    async def close(self) -> None:
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        self._initialized = False
        logger.info("Redis连接已关闭")

    async def get(self, key: str) -> Optional[str]:
        """
        获取值

        Args:
            key: 键

        Returns:
            Optional[str]: 值，如果不存在返回None
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET操作失败: {str(e)}", extra={'key': key})
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        设置值

        Args:
            key: 键
            value: 值
            expire: 过期时间（秒），可选

        Returns:
            bool: 是否成功
        """
        if not self._initialized:
            await self.initialize()

        try:
            # 序列化复杂对象
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)

            result = await self._client.set(key, value, ex=expire)
            return bool(result)

        except Exception as e:
            logger.error(f"Redis SET操作失败: {str(e)}", extra={'key': key, 'expire': expire})
            return False

    async def delete(self, *keys: str) -> int:
        """
        删除键

        Args:
            *keys: 一个或多个键

        Returns:
            int: 删除的键数量
        """
        if not self._initialized:
            await self.initialize()

        if not keys:
            return 0

        try:
            return await self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE操作失败: {str(e)}", extra={'keys': keys})
            return 0

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键

        Returns:
            bool: 是否存在
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = await self._client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS操作失败: {str(e)}", extra={'key': key})
            return False

    async def expire(self, key: str, expire: int) -> bool:
        """
        设置过期时间

        Args:
            key: 键
            expire: 过期时间（秒）

        Returns:
            bool: 是否成功
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = await self._client.expire(key, expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXPIRE操作失败: {str(e)}", extra={'key': key, 'expire': expire})
            return False

    async def get_ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间

        Args:
            key: 键

        Returns:
            int: TTL（秒），-1表示永不过期，-2表示不存在
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL操作失败: {str(e)}", extra={'key': key})
            return -2

    async def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希字段值

        Args:
            name: 哈希名称
            key: 字段名

        Returns:
            Optional[str]: 字段值
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self._client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET操作失败: {str(e)}", extra={'name': name, 'key': key})
            return None

    async def hset(self, name: str, key: str, value: Any) -> bool:
        """
        设置哈希字段值

        Args:
            name: 哈希名称
            key: 字段名
            value: 字段值

        Returns:
            bool: 是否成功
        """
        if not self._initialized:
            await self.initialize()

        try:
            # 序列化复杂对象
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)

            result = await self._client.hset(name, key, value)
            return bool(result)

        except Exception as e:
            logger.error(f"Redis HSET操作失败: {str(e)}", extra={'name': name, 'key': key})
            return False

    async def hgetall(self, name: str) -> Dict[str, str]:
        """
        获取哈希所有字段

        Args:
            name: 哈希名称

        Returns:
            Dict[str, str]: 字段字典
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self._client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL操作失败: {str(e)}", extra={'name': name})
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希字段

        Args:
            name: 哈希名称
            *keys: 一个或多个字段名

        Returns:
            int: 删除的字段数量
        """
        if not self._initialized:
            await self.initialize()

        if not keys:
            return 0

        try:
            return await self._client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL操作失败: {str(e)}", extra={'name': name, 'keys': keys})
            return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        增加数值

        Args:
            key: 键
            amount: 增加量

        Returns:
            int: 增加后的值
        """
        if not self._initialized:
            await self.initialize()

        try:
            return await self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR操作失败: {str(e)}", extra={'key': key, 'amount': amount})
            return 0


# 全局Redis客户端实例
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """获取Redis客户端依赖注入"""
    if not redis_client._initialized:
        await redis_client.initialize()
    return redis_client
