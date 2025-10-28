# 图片URL管理系统实现指南

## 1. 代码组织结构

### 1.1 后端新增文件结构
```
backend/
├── app/
│   ├── core/
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # Redis客户端连接管理
│   │   │   ├── cache_manager.py       # 缓存管理核心类
│   │   │   └── url_cache.py           # URL专用缓存逻辑
│   │   │
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── base_task.py           # 任务基类
│   │   │   ├── scheduler.py           # 任务调度器
│   │   │   └── url_refresh_task.py    # URL刷新定时任务
│   │   │
│   │   └── monitoring/
│   │       ├── __init__.py
│   │       ├── metrics.py             # 监控指标收集
│   │       └── health_check.py        # 健康检查
│   │
│   ├── services/
│   │   └── image/
│   │       ├── url_manager.py         # URL生命周期管理服务
│   │       ├── proxy_service.py       # 图片代理服务
│   │       ├── cache_service.py       # 缓存操作服务
│   │       └── refresh_service.py     # URL刷新服务
│   │
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── image_proxy.py     # 图片代理API端点
│   │           └── image_monitoring.py # 监控API端点
│   │
│   ├── schemas/
│   │   ├── image_url.py               # URL相关的Pydantic模型
│   │   └── monitoring.py              # 监控数据模型
│   │
│   └── utils/
│       ├── cache_utils.py             # 缓存工具函数
│       └── url_utils.py               # URL处理工具函数
```

### 1.2 前端新增/修改文件
```
frontend/src/
├── services/
│   ├── imageProxy.ts                  # 新增：图片代理服务
│   └── image.ts                       # 修改：增强错误处理和重试机制
│
├── components/
│   ├── common/
│   │   └── SmartImage.vue            # 新增：智能图片组件
│   │
│   └── image/
│       └── ImageManager.vue           # 修改：使用新的图片服务
│
├── composables/
│   ├── useImageCache.ts              # 新增：前端图片缓存
│   ├── useImageRetry.ts              # 新增：图片重试逻辑
│   └── useImageMonitoring.ts         # 新增：前端监控
│
└── utils/
    ├── imageUtils.ts                 # 增强：图片处理工具
    └── retryUtils.ts                 # 新增：重试工具函数
```

## 2. 核心代码实现

### 2.1 Redis客户端管理

#### `backend/app/core/redis/client.py`
```python
"""
Redis客户端连接管理
"""
import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis异步客户端单例"""
    
    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None
    _pool: Optional[ConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> redis.Redis:
        """建立Redis连接"""
        if self._client is None:
            try:
                self._pool = ConnectionPool.from_url(
                    settings.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                self._client = redis.Redis(
                    connection_pool=self._pool,
                    decode_responses=True
                )
                
                # 测试连接
                await self._client.ping()
                logger.info("Redis连接建立成功")
                
            except Exception as e:
                logger.error(f"Redis连接失败: {e}")
                raise
                
        return self._client

    async def disconnect(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis连接已关闭")

    async def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            await self.connect()
        return self._client

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            client = await self.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return False


# 全局Redis客户端实例
redis_client = RedisClient()


async def get_redis() -> redis.Redis:
    """依赖注入用的Redis客户端获取函数"""
    return await redis_client.get_client()
```

#### `backend/app/core/redis/url_cache.py`
```python
"""
图片URL专用缓存逻辑
"""
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.redis.client import get_redis
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageURLCache:
    """图片URL缓存管理器"""
    
    def __init__(self):
        self.url_key_prefix = "image:url:"
        self.stats_key_prefix = "image:stats:"
        self.queue_key = "image:refresh:queue"
        self.lock_key_prefix = "image:refresh:lock:"
        
    async def get_url(self, image_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的URL信息"""
        try:
            redis = await get_redis()
            cache_key = f"{self.url_key_prefix}{image_id}"
            
            cached_data = await redis.get(cache_key)
            if not cached_data:
                return None
                
            url_info = json.loads(cached_data)
            
            # 检查是否过期
            if url_info.get('expires_at', 0) <= time.time():
                await redis.delete(cache_key)
                return None
                
            # 更新访问计数
            url_info['access_count'] = url_info.get('access_count', 0) + 1
            url_info['last_access'] = time.time()
            
            await redis.setex(
                cache_key,
                int(url_info['expires_at'] - time.time()) + 300,  # 5分钟缓冲
                json.dumps(url_info)
            )
            
            return url_info
            
        except Exception as e:
            logger.error(f"获取URL缓存失败: {e}", extra={'image_id': image_id})
            return None
    
    async def set_url(
        self, 
        image_id: str, 
        url: str, 
        expires_at: int,
        cos_key: str = None
    ) -> bool:
        """设置URL缓存"""
        try:
            redis = await get_redis()
            cache_key = f"{self.url_key_prefix}{image_id}"
            
            url_info = {
                'url': url,
                'expires_at': expires_at,
                'created_at': time.time(),
                'access_count': 0,
                'cos_key': cos_key
            }
            
            ttl = int(expires_at - time.time()) + 300  # 5分钟缓冲
            if ttl > 0:
                await redis.setex(cache_key, ttl, json.dumps(url_info))
                
                # 添加到刷新队列（如果即将过期）
                refresh_threshold = 900  # 15分钟
                if ttl <= refresh_threshold:
                    await self.add_to_refresh_queue(image_id)
                    
                return True
            return False
            
        except Exception as e:
            logger.error(f"设置URL缓存失败: {e}", extra={'image_id': image_id})
            return False
    
    async def add_to_refresh_queue(self, image_id: str) -> bool:
        """添加到刷新队列"""
        try:
            redis = await get_redis()
            # 使用集合避免重复
            await redis.sadd(self.queue_key, image_id)
            return True
        except Exception as e:
            logger.error(f"添加刷新队列失败: {e}", extra={'image_id': image_id})
            return False
    
    async def get_refresh_queue(self, limit: int = 100) -> List[str]:
        """获取待刷新的图片ID列表"""
        try:
            redis = await get_redis()
            # 获取并移除元素
            image_ids = []
            for _ in range(limit):
                image_id = await redis.spop(self.queue_key)
                if not image_id:
                    break
                image_ids.append(image_id)
            return image_ids
        except Exception as e:
            logger.error(f"获取刷新队列失败: {e}")
            return []
    
    async def acquire_refresh_lock(self, image_id: str, timeout: int = 300) -> bool:
        """获取刷新锁"""
        try:
            redis = await get_redis()
            lock_key = f"{self.lock_key_prefix}{image_id}"
            
            # 使用SET NX EX实现分布式锁
            result = await redis.set(
                lock_key, 
                str(time.time()), 
                nx=True, 
                ex=timeout
            )
            return bool(result)
        except Exception as e:
            logger.error(f"获取刷新锁失败: {e}", extra={'image_id': image_id})
            return False
    
    async def release_refresh_lock(self, image_id: str) -> bool:
        """释放刷新锁"""
        try:
            redis = await get_redis()
            lock_key = f"{self.lock_key_prefix}{image_id}"
            await redis.delete(lock_key)
            return True
        except Exception as e:
            logger.error(f"释放刷新锁失败: {e}", extra={'image_id': image_id})
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            redis = await get_redis()
            
            # 获取所有URL缓存键
            url_keys = await redis.keys(f"{self.url_key_prefix}*")
            total_cached = len(url_keys)
            
            # 计算即将过期的数量
            expiring_soon = 0
            current_time = time.time()
            
            for key in url_keys[:100]:  # 采样检查
                cached_data = await redis.get(key)
                if cached_data:
                    url_info = json.loads(cached_data)
                    if url_info.get('expires_at', 0) - current_time <= 900:  # 15分钟内过期
                        expiring_soon += 1
            
            # 获取队列长度
            queue_length = await redis.scard(self.queue_key)
            
            return {
                'total_cached_urls': total_cached,
                'expiring_soon': expiring_soon,
                'refresh_queue_length': queue_length,
                'cache_hit_rate': 0.0,  # 需要通过其他方式计算
                'last_updated': current_time
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局URL缓存实例
url_cache = ImageURLCache()
```

### 2.2 URL管理服务

#### `backend/app/services/image/url_manager.py`
```python
"""
图片URL生命周期管理服务
"""
import time
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis.url_cache import url_cache
from app.core.storage.cos_storage import COSStorage
from app.repositories.image import ImageRepository
from app.core.log_utils import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ImageURLManager:
    """图片URL管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.image_repo = ImageRepository(db)
        self.storage = COSStorage()
        
    async def get_image_url(
        self, 
        image_id: str, 
        user_id: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        获取图片访问URL
        
        Args:
            image_id: 图片ID
            user_id: 用户ID
            force_refresh: 是否强制刷新
            
        Returns:
            包含URL和元信息的字典
        """
        try:
            # 1. 检查缓存（除非强制刷新）
            if not force_refresh:
                cached_url = await url_cache.get_url(image_id)
                if cached_url:
                    return {
                        'url': cached_url['url'],
                        'expires_at': cached_url['expires_at'],
                        'from_cache': True,
                        'access_count': cached_url.get('access_count', 0)
                    }
            
            # 2. 从数据库获取图片信息
            image = await self.image_repo.get_by_id(image_id)
            if not image or image.user_id != user_id:
                raise ValueError(f"图片不存在或无权访问: {image_id}")
            
            # 3. 生成新的预签名URL
            if not image.cos_key:
                raise ValueError(f"图片缺少COS存储信息: {image_id}")
            
            expires_seconds = settings.cos_url_expires
            presigned_url = await self.storage.generate_url(
                image.cos_key,
                expires=expires_seconds,
                operation="get"
            )
            
            expires_at = time.time() + expires_seconds
            
            # 4. 缓存新URL
            await url_cache.set_url(
                image_id,
                presigned_url,
                int(expires_at),
                image.cos_key
            )
            
            # 5. 记录日志
            logger.info(
                "生成图片URL成功",
                extra={
                    'image_id': image_id,
                    'user_id': user_id,
                    'expires_at': expires_at,
                    'force_refresh': force_refresh
                }
            )
            
            return {
                'url': presigned_url,
                'expires_at': int(expires_at),
                'from_cache': False,
                'cos_key': image.cos_key
            }
            
        except Exception as e:
            logger.error(
                f"获取图片URL失败: {e}",
                extra={'image_id': image_id, 'user_id': user_id}
            )
            raise
    
    async def refresh_url(self, image_id: str) -> bool:
        """
        刷新指定图片的URL
        
        Args:
            image_id: 图片ID
            
        Returns:
            是否刷新成功
        """
        try:
            # 获取刷新锁
            if not await url_cache.acquire_refresh_lock(image_id):
                logger.warning(f"无法获取刷新锁: {image_id}")
                return False
            
            try:
                # 获取图片信息
                image = await self.image_repo.get_by_id(image_id)
                if not image or not image.cos_key:
                    return False
                
                # 生成新URL
                expires_seconds = settings.cos_url_expires
                presigned_url = await self.storage.generate_url(
                    image.cos_key,
                    expires=expires_seconds,
                    operation="get"
                )
                
                expires_at = time.time() + expires_seconds
                
                # 更新缓存
                success = await url_cache.set_url(
                    image_id,
                    presigned_url,
                    int(expires_at),
                    image.cos_key
                )
                
                if success:
                    logger.info(f"URL刷新成功: {image_id}")
                    
                return success
                
            finally:
                # 释放锁
                await url_cache.release_refresh_lock(image_id)
                
        except Exception as e:
            logger.error(f"URL刷新失败: {e}", extra={'image_id': image_id})
            return False
    
    async def batch_refresh_urls(self, image_ids: list, max_concurrent: int = 10) -> Dict[str, bool]:
        """
        批量刷新URL
        
        Args:
            image_ids: 图片ID列表
            max_concurrent: 最大并发数
            
        Returns:
            刷新结果字典
        """
        import asyncio
        
        async def refresh_single(image_id: str) -> tuple:
            result = await self.refresh_url(image_id)
            return image_id, result
        
        # 限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def refresh_with_semaphore(image_id: str):
            async with semaphore:
                return await refresh_single(image_id)
        
        # 执行批量刷新
        tasks = [refresh_with_semaphore(image_id) for image_id in image_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        refresh_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量刷新出现异常: {result}")
                continue
            image_id, success = result
            refresh_results[image_id] = success
        
        return refresh_results
```

### 2.3 图片代理服务

#### `backend/app/api/v1/endpoints/image_proxy.py`
```python
"""
图片代理API端点
提供永不过期的图片访问接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import aiohttp
import asyncio

from app.db.database import get_db
from app.services.image.url_manager import ImageURLManager
from app.core.log_utils import get_logger
from app.schemas.common import StandardResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/images", tags=["Image Proxy"])


@router.get(
    "/{image_id}/proxy",
    summary="图片代理访问",
    description="提供永不过期的图片访问代理服务"
)
async def proxy_image(
    image_id: str,
    redirect: Optional[bool] = False,
    db: AsyncSession = Depends(get_db)
):
    """
    图片代理访问端点
    
    Args:
        image_id: 图片ID
        redirect: 是否重定向到预签名URL（默认false，返回图片流）
        db: 数据库会话
        
    Returns:
        图片流或重定向响应
    """
    try:
        # TODO: 从认证中获取用户ID
        user_id = "demo_001"
        
        # 获取图片URL
        url_manager = ImageURLManager(db)
        url_info = await url_manager.get_image_url(image_id, user_id)
        
        if redirect:
            # 重定向模式：直接重定向到预签名URL
            return RedirectResponse(
                url=url_info['url'],
                status_code=status.HTTP_302_FOUND
            )
        else:
            # 代理模式：流式返回图片内容
            return await _stream_image(url_info['url'])
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"图片代理失败: {e}",
            extra={'image_id': image_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="图片访问失败"
        )


async def _stream_image(url: str) -> StreamingResponse:
    """
    流式返回图片内容
    
    Args:
        url: 图片URL
        
    Returns:
        StreamingResponse
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="图片不存在"
                    )
                
                content_type = response.headers.get('content-type', 'image/jpeg')
                content_length = response.headers.get('content-length')
                
                async def generate():
                    async for chunk in response.content.iter_chunked(8192):
                        yield chunk
                
                headers = {'content-type': content_type}
                if content_length:
                    headers['content-length'] = content_length
                
                return StreamingResponse(
                    generate(),
                    media_type=content_type,
                    headers=headers
                )
                
    except aiohttp.ClientError as e:
        logger.error(f"下载图片失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="图片下载失败"
        )


@router.get(
    "/{image_id}/url/refresh",
    response_model=StandardResponse,
    summary="刷新图片URL",
    description="强制刷新指定图片的访问URL"
)
async def refresh_image_url(
    image_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    刷新图片URL
    
    Args:
        image_id: 图片ID
        db: 数据库会话
        
    Returns:
        StandardResponse
    """
    try:
        # TODO: 从认证中获取用户ID
        user_id = "demo_001"
        
        # 强制刷新URL
        url_manager = ImageURLManager(db)
        url_info = await url_manager.get_image_url(
            image_id, 
            user_id, 
            force_refresh=True
        )
        
        return StandardResponse(
            status="success",
            message="URL刷新成功",
            data={
                'image_id': image_id,
                'url': url_info['url'],
                'expires_at': url_info['expires_at']
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"刷新图片URL失败: {e}",
            extra={'image_id': image_id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="URL刷新失败"
        )
```

### 2.4 前端智能图片组件

#### `frontend/src/components/common/SmartImage.vue`
```vue
<template>
  <div class="smart-image-container">
    <img
      ref="imageRef"
      :src="currentSrc"
      :alt="alt"
      :class="imageClass"
      @load="handleLoad"
      @error="handleError"
      @click="handleClick"
    />
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <span class="loading-text">图片加载中...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-if="error && !loading" class="error-overlay">
      <div class="error-icon">⚠️</div>
      <span class="error-text">图片加载失败</span>
      <button class="retry-button" @click="handleRetry">重试</button>
    </div>
    
    <!-- 占位图 -->
    <div v-if="showPlaceholder" class="placeholder-overlay">
      <div class="placeholder-icon">🖼️</div>
      <span class="placeholder-text">暂无图片</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useImageRetry } from '@/composables/useImageRetry'
import { useImageCache } from '@/composables/useImageCache'
import { getImageAccessUrl } from '@/services/image'

interface Props {
  imageId?: string
  src?: string
  alt?: string
  fallbackSrc?: string
  maxRetries?: number
  retryDelay?: number
  useProxy?: boolean
  class?: string
}

interface Emits {
  (e: 'load', event: Event): void
  (e: 'error', error: Error): void
  (e: 'retry', attempt: number): void
}

const props = withDefaults(defineProps<Props>(), {
  alt: '',
  maxRetries: 3,
  retryDelay: 1000,
  useProxy: false,
  class: ''
})

const emit = defineEmits<Emits>()

// 响应式状态
const imageRef = ref<HTMLImageElement>()
const currentSrc = ref('')
const loading = ref(false)
const error = ref(false)
const retryCount = ref(0)

// 组合式函数
const { retryWithBackoff } = useImageRetry()
const { getCachedUrl, setCachedUrl } = useImageCache()

// 计算属性
const imageClass = computed(() => {
  const classes = ['smart-image']
  if (props.class) classes.push(props.class)
  if (loading.value) classes.push('loading')
  if (error.value) classes.push('error')
  return classes.join(' ')
})

const showPlaceholder = computed(() => {
  return !props.src && !props.imageId && !loading.value
})

// 获取图片URL
const getImageUrl = async (): Promise<string> => {
  if (props.src) {
    return props.src
  }
  
  if (props.imageId) {
    // 检查缓存
    const cachedUrl = getCachedUrl(props.imageId)
    if (cachedUrl && !isUrlExpired(cachedUrl)) {
      return cachedUrl.url
    }
    
    // 从服务器获取
    if (props.useProxy) {
      // 使用代理服务
      return `/api/v1/images/${props.imageId}/proxy`
    } else {
      // 获取预签名URL
      const response = await getImageAccessUrl(props.imageId)
      const urlInfo = {
        url: response.url,
        expiresAt: Date.now() + (50 * 60 * 1000), // 假设50分钟过期
        imageId: props.imageId
      }
      setCachedUrl(props.imageId, urlInfo)
      return response.url
    }
  }
  
  throw new Error('没有提供有效的图片源')
}

// 检查URL是否过期
const isUrlExpired = (urlInfo: any): boolean => {
  return Date.now() > urlInfo.expiresAt
}

// 加载图片
const loadImage = async (force = false) => {
  if (loading.value && !force) return
  
  try {
    loading.value = true
    error.value = false
    
    const url = await getImageUrl()
    currentSrc.value = url
    
  } catch (err) {
    console.error('获取图片URL失败:', err)
    error.value = true
    emit('error', err as Error)
    
    // 尝试使用备用URL
    if (props.fallbackSrc && currentSrc.value !== props.fallbackSrc) {
      currentSrc.value = props.fallbackSrc
    }
  } finally {
    loading.value = false
  }
}

// 事件处理
const handleLoad = (event: Event) => {
  loading.value = false
  error.value = false
  retryCount.value = 0
  emit('load', event)
}

const handleError = async (event: Event) => {
  loading.value = false
  error.value = true
  
  // 自动重试逻辑
  if (retryCount.value < props.maxRetries) {
    retryCount.value++
    emit('retry', retryCount.value)
    
    await retryWithBackoff(
      () => loadImage(true),
      retryCount.value,
      props.retryDelay
    )
  } else {
    emit('error', new Error('图片加载失败，已达到最大重试次数'))
  }
}

const handleRetry = () => {
  retryCount.value = 0
  loadImage(true)
}

const handleClick = (event: Event) => {
  // 如果是错误状态，点击重试
  if (error.value) {
    handleRetry()
  }
}

// 监听属性变化
watch([() => props.src, () => props.imageId], () => {
  retryCount.value = 0
  loadImage()
}, { immediate: true })

// 组件挂载
onMounted(() => {
  if (props.src || props.imageId) {
    loadImage()
  }
})
</script>

<style scoped>
.smart-image-container {
  position: relative;
  display: inline-block;
  overflow: hidden;
}

.smart-image {
  display: block;
  max-width: 100%;
  height: auto;
  transition: opacity 0.3s ease;
}

.smart-image.loading {
  opacity: 0.7;
}

.smart-image.error {
  opacity: 0.5;
}

.loading-overlay,
.error-overlay,
.placeholder-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(2px);
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text,
.error-text,
.placeholder-text {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
  text-align: center;
}

.error-icon,
.placeholder-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.retry-button {
  margin-top: 8px;
  padding: 4px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.retry-button:hover {
  background: #0056b3;
}
</style>
```

### 2.5 定时刷新任务

#### `backend/app/core/tasks/url_refresh_task.py`
```python
"""
URL刷新定时任务
"""
import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.redis.url_cache import url_cache
from app.db.database import get_async_session
from app.services.image.url_manager import ImageURLManager
from app.core.log_utils import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class URLRefreshTask:
    """URL刷新定时任务"""
    
    def __init__(self):
        self.running = False
        self.stats = {
            'last_run': None,
            'total_refreshed': 0,
            'success_count': 0,
            'error_count': 0
        }
    
    async def start(self):
        """启动定时任务"""
        if self.running:
            logger.warning("URL刷新任务已在运行")
            return
        
        self.running = True
        logger.info("URL刷新任务启动")
        
        try:
            while self.running:
                await self._run_refresh_cycle()
                # 等待下一次执行（默认5分钟）
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"URL刷新任务异常退出: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """停止定时任务"""
        self.running = False
        logger.info("URL刷新任务停止")
    
    async def _run_refresh_cycle(self):
        """执行一次刷新周期"""
        try:
            start_time = time.time()
            self.stats['last_run'] = datetime.now()
            
            # 获取待刷新的图片ID列表
            batch_size = getattr(settings, 'url_prerefresh_batch_size', 100)
            image_ids = await url_cache.get_refresh_queue(batch_size)
            
            if not image_ids:
                logger.debug("没有需要刷新的URL")
                return
            
            logger.info(f"开始刷新URL批次，数量: {len(image_ids)}")
            
            # 批量刷新
            async with get_async_session() as db:
                url_manager = ImageURLManager(db)
                refresh_results = await url_manager.batch_refresh_urls(image_ids)
            
            # 统计结果
            success_count = sum(1 for success in refresh_results.values() if success)
            error_count = len(refresh_results) - success_count
            
            self.stats['total_refreshed'] += len(refresh_results)
            self.stats['success_count'] += success_count
            self.stats['error_count'] += error_count
            
            elapsed = time.time() - start_time
            
            logger.info(
                f"URL刷新批次完成",
                extra={
                    'batch_size': len(image_ids),
                    'success_count': success_count,
                    'error_count': error_count,
                    'elapsed_seconds': elapsed
                }
            )
            
        except Exception as e:
            logger.error(f"URL刷新周期执行失败: {e}")
            self.stats['error_count'] += 1
    
    async def refresh_expiring_urls(self):
        """主动发现并刷新即将过期的URL"""
        try:
            # 这里可以实现更智能的过期检测逻辑
            # 比如扫描Redis中即将过期的键
            pass
        except Exception as e:
            logger.error(f"主动刷新过期URL失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        return {
            **self.stats,
            'running': self.running,
            'success_rate': (
                self.stats['success_count'] / self.stats['total_refreshed']
                if self.stats['total_refreshed'] > 0 else 0
            )
        }


# 全局任务实例
url_refresh_task = URLRefreshTask()
```

## 3. 配置和部署

### 3.1 配置文件修改

#### `backend/app/core/config.py` 新增配置项
```python
# URL缓存配置
url_cache_enabled: bool = True
url_cache_default_ttl: int = 3600  # 1小时
url_cache_max_size: int = 10000

# 预刷新配置
url_prerefresh_enabled: bool = True
url_prerefresh_threshold: int = 900  # 15分钟
url_prerefresh_batch_size: int = 100

# 代理服务配置
image_proxy_enabled: bool = True
image_proxy_timeout: int = 30
image_proxy_retry_count: int = 3

# 监控配置
url_stats_enabled: bool = True
url_stats_retention_days: int = 30
```

### 3.2 应用启动修改

#### `backend/main.py` 修改
```python
from app.core.tasks.url_refresh_task import url_refresh_task
from app.core.redis.client import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    await redis_client.connect()
    
    # 启动URL刷新任务
    if settings.url_prerefresh_enabled:
        asyncio.create_task(url_refresh_task.start())
    
    yield
    
    # 关闭时
    await url_refresh_task.stop()
    await redis_client.disconnect()

app = FastAPI(lifespan=lifespan)
```

## 4. 部署检查清单

### 4.1 环境配置
- [ ] Redis服务正常运行
- [ ] 环境变量配置正确
- [ ] COS访问权限验证

### 4.2 功能测试
- [ ] URL缓存功能测试
- [ ] 代理服务访问测试
- [ ] 前端图片显示测试
- [ ] 定时刷新任务测试

### 4.3 性能测试
- [ ] 缓存命中率监控
- [ ] 响应时间测试
- [ ] 并发访问测试
- [ ] 内存使用监控

### 4.4 监控告警
- [ ] Redis连接状态监控
- [ ] URL刷新任务状态监控
- [ ] 图片访问成功率监控
- [ ] 系统资源使用监控

---

**文档版本**：v1.0  
**更新时间**：2024年12月  
**适用版本**：ai-pptist v1.0+  
