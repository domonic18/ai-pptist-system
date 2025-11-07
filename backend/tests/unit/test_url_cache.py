"""
URL缓存单元测试
测试ImageURLCache的各种功能
"""

import pytest
import time
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.cache.url_cache import (
    ImageURLCache, URLCacheEntry, CacheStrategy
)
from app.core.redis import RedisClient


class TestURLCacheEntry:
    """测试URLCacheEntry数据类"""

    def test_entry_creation(self):
        """测试创建缓存条目"""
        now = time.time()
        entry = URLCacheEntry(
            url="https://example.com/image.jpg",
            expires_at=now + 3600,
            image_key="test_image_key",
            mime_type="image/jpeg"
        )

        assert entry.url == "https://example.com/image.jpg"
        assert entry.image_key == "test_image_key"
        assert entry.mime_type == "image/jpeg"
        assert entry.access_count == 0
        # 允许微小的时间差异
        assert abs(entry.created_at - now) < 0.1
        assert abs(entry.last_accessed - now) < 0.1

    def test_entry_is_expired(self):
        """测试检查过期"""
        entry = URLCacheEntry(
            url="https://example.com/image.jpg",
            expires_at=time.time() - 100  # 已过期
        )

        assert entry.is_expired() is True

        entry2 = URLCacheEntry(
            url="https://example.com/image.jpg",
            expires_at=time.time() + 3600  # 未过期
        )

        assert entry2.is_expired() is False

    def test_entry_access(self):
        """测试记录访问"""
        entry = URLCacheEntry(
            url="https://example.com/image.jpg",
            expires_at=time.time() + 3600
        )

        assert entry.access_count == 0
        assert entry.last_accessed > 0

        old_last_accessed = entry.last_accessed

        entry.access()

        assert entry.access_count == 1
        assert entry.last_accessed > old_last_accessed

    def test_entry_to_dict(self):
        """测试转换为字典"""
        now = time.time()
        entry = URLCacheEntry(
            url="https://example.com/image.jpg",
            expires_at=now + 3600,
            access_count=5,
            image_key="test_key"
        )

        data = entry.to_dict()

        assert data['url'] == "https://example.com/image.jpg"
        assert data['expires_at'] == now + 3600
        assert data['access_count'] == 5
        assert data['image_key'] == "test_key"

    def test_entry_from_dict(self):
        """测试从字典创建"""
        data = {
            'url': "https://example.com/image.jpg",
            'expires_at': time.time() + 3600,
            'access_count': 3,
            'created_at': time.time() - 100,
            'last_accessed': time.time() - 50,
            'image_key': "test_key",
            'mime_type': "image/jpeg"
        }

        entry = URLCacheEntry.from_dict(data)

        assert entry.url == "https://example.com/image.jpg"
        assert entry.access_count == 3
        assert entry.image_key == "test_key"
        assert entry.mime_type == "image/jpeg"


class TestImageURLCache:
    """测试ImageURLCache类"""

    @pytest.fixture
    def mock_redis(self):
        """创建模拟Redis"""
        mock = Mock(spec=RedisClient)
        mock._client = Mock()
        return mock

    @pytest.fixture
    def cache(self, mock_redis):
        """创建缓存实例"""
        cache = ImageURLCache(
            cache_ttl=3600,
            pre_refresh_threshold=900,
            max_cache_size=1000,
            strategy=CacheStrategy.LRU
        )
        cache.redis = mock_redis
        return cache

    def test_cache_key_generation(self, cache):
        """测试缓存键生成"""
        assert cache._get_cache_key("test_key") == "image:url:test_key"
        assert cache._get_stats_key("test_key") == "image:url:stats:test_key"

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache, mock_redis):
        """测试设置和获取缓存"""
        # 设置缓存
        await cache.set(
            image_key="test_image",
            url="https://example.com/image.jpg",
            expires_in=3600,
            mime_type="image/jpeg"
        )

        # 验证设置调用
        assert mock_redis.set.called
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "image:url:test_image"
        assert call_args[1]['expire'] == 3600

    @pytest.mark.asyncio
    async def test_get_not_found(self, cache, mock_redis):
        """测试获取不存在的缓存"""
        mock_redis.get.return_value = None

        result = await cache.get("nonexistent")

        assert result is None
        assert cache.stats['misses'] == 1

    @pytest.mark.asyncio
    async def test_get_expired(self, cache, mock_redis):
        """测试获取已过期的缓存"""
        expired_data = {
            'url': "https://example.com/image.jpg",
            'expires_at': time.time() - 100,
            'access_count': 0,
            'created_at': time.time() - 200,
            'last_accessed': time.time() - 100,
            'image_key': "test",
            'mime_type': "image/jpeg"
        }

        mock_redis.get.return_value = json.dumps(expired_data)
        mock_redis.delete = AsyncMock()

        result = await cache.get("test")

        assert result is None
        assert mock_redis.delete.called
        assert cache.stats['expired'] == 1

    @pytest.mark.asyncio
    async def test_get_valid(self, cache, mock_redis):
        """测试获取有效的缓存"""
        now = time.time()
        valid_data = {
            'url': "https://example.com/image.jpg",
            'expires_at': now + 3600,
            'access_count': 0,
            'created_at': now,
            'last_accessed': now,
            'image_key': "test",
            'mime_type': "image/jpeg"
        }

        mock_redis.get.return_value = json.dumps(valid_data)
        mock_redis.set = AsyncMock()

        result = await cache.get("test")

        assert result is not None
        assert result.url == "https://example.com/image.jpg"
        assert result.access_count == 1  # 访问后增加
        assert cache.stats['hits'] == 1

    @pytest.mark.asyncio
    async def test_delete(self, cache, mock_redis):
        """测试删除缓存"""
        mock_redis.delete = AsyncMock()

        await cache.delete("test")

        assert mock_redis.delete.called
        assert mock_redis.delete.call_args[0][0] == "image:url:test"

    @pytest.mark.asyncio
    async def test_is_near_expiry(self, cache, mock_redis):
        """测试检查即将过期"""
        # 即将过期
        near_expiry_data = {
            'url': "https://example.com/image.jpg",
            'expires_at': time.time() + 500,  # 不到阈值
            'access_count': 0,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'image_key': "test",
            'mime_type': "image/jpeg"
        }

        mock_redis.get.return_value = json.dumps(near_expiry_data)

        result = await cache.is_near_expiry("test", threshold=600)
        assert result is True

        # 不会过期
        not_near_expiry_data = {
            'url': "https://example.com/image.jpg",
            'expires_at': time.time() + 2000,  # 超过阈值
            'access_count': 0,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'image_key': "test",
            'mime_type': "image/jpeg"
        }

        mock_redis.get.return_value = json.dumps(not_near_expiry_data)

        result = await cache.is_near_expiry("test", threshold=600)
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache, mock_redis):
        """测试清理过期缓存"""
        # 模拟一些过期的键
        expired_keys = ["image:url:expired1", "image:url:expired2", "image:url:valid1"]

        async def mock_keys(pattern):
            if pattern == "image:url:*":
                return expired_keys
            return []

        mock_redis._client.keys = AsyncMock(side_effect=mock_keys)
        mock_redis.get.side_effect = [
            json.dumps({
                'url': "https://example.com/expired1.jpg",
                'expires_at': time.time() - 100,
                'access_count': 0,
                'created_at': time.time() - 200,
                'last_accessed': time.time() - 100,
                'image_key': "expired1",
                'mime_type': "image/jpeg"
            }),
            json.dumps({
                'url': "https://example.com/expired2.jpg",
                'expires_at': time.time() - 50,
                'access_count': 0,
                'created_at': time.time() - 150,
                'last_accessed': time.time() - 50,
                'image_key': "expired2",
                'mime_type': "image/jpeg"
            }),
            json.dumps({
                'url': "https://example.com/valid1.jpg",
                'expires_at': time.time() + 3600,
                'access_count': 0,
                'created_at': time.time(),
                'last_accessed': time.time(),
                'image_key': "valid1",
                'mime_type': "image/jpeg"
            })
        ]
        mock_redis.delete = AsyncMock()

        cleaned = await cache.cleanup_expired()

        assert cleaned == 2
        # 验证删除调用 - 每次批量删除会调用一次delete，包含多个键
        assert mock_redis.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, cache, mock_redis):
        """测试获取统计信息"""
        cache.stats = {
            'hits': 80,
            'misses': 20,
            'expired': 5,
            'refreshed': 10,
            'errors': 2
        }

        mock_redis._client.keys = AsyncMock(return_value=["key1", "key2", "key3"])

        stats = await cache.get_stats()

        assert 'total_keys' in stats
        assert stats['total_keys'] == 3
        assert stats['hit_rate'] == 80.0
        assert stats['stats']['hits'] == 80
        assert stats['stats']['misses'] == 20

    @pytest.mark.asyncio
    async def test_clear_all(self, cache, mock_redis):
        """测试清空所有缓存"""
        mock_redis._client.keys = AsyncMock(return_value=["key1", "key2"])
        mock_redis.delete = AsyncMock(return_value=True)

        result = await cache.clear_all()

        assert result is True
        assert mock_redis.delete.called
        assert cache.stats == {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'refreshed': 0,
            'errors': 0
        }
