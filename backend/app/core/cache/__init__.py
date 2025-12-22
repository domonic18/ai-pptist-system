"""
缓存模块
包含Redis客户端和缓存操作
"""

from app.core.cache.redis import redis_client, get_redis

__all__ = ["redis_client", "get_redis"]