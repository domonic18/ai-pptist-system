"""
图片代理API端点
提供图片代理访问服务，支持代理模式和重定向模式
"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.cache.image_proxy_handler import ImageProxyHandler
from app.core.log_utils import get_logger
from app.schemas.common import StandardResponse

logger = get_logger(__name__)

router = APIRouter(tags=["图片代理"])


@router.get(
    "/{image_key:path}",
    summary="图片代理访问",
    description="通过代理模式或重定向模式访问图片，支持缓存加速"
)
async def proxy_image(
    image_key: str,
    request: Request,
    mode: str = Query("redirect", regex="^(redirect|proxy)$", description="访问模式：redirect(重定向)或proxy(代理)"),
    refresh: bool = Query(False, description="是否强制刷新URL"),
    db: AsyncSession = Depends(get_db)
):
    """
    图片代理访问端点

    支持两种模式：
    1. redirect模式：返回302重定向到预签名URL（推荐，性能最佳）
    2. proxy模式：通过后端代理转发图片内容（兼容性最好）

    Args:
        image_key: 图片在COS中的存储键
        request: FastAPI请求对象
        mode: 访问模式
        refresh: 是否强制刷新URL
        db: 数据库会话

    Returns:
        StreamingResponse: 代理模式的图片流
        RedirectResponse: 重定向模式的302响应
    """
    start_time = time.time()
    handler = ImageProxyHandler(db)

    # 获取图片URL（使用缓存）
    url, metadata = await handler.handle_get_image_url(
        image_key=image_key,
        force_refresh=refresh
    )

    response_time = time.time() - start_time

    logger.info(
        f"图片代理访问: {image_key}",
        extra={
            'image_key': image_key,
            'mode': mode,
            'from_cache': metadata.get('from_cache', False),
            'response_time': response_time
        }
    )

    # 根据模式返回不同响应
    if mode == "redirect":
        # 重定向模式：返回302跳转
        logger.debug(f"使用重定向模式访问: {image_key}")
        return RedirectResponse(
            url=url,
            status_code=302,
            headers={
                'Cache-Control': 'public, max-age=300',  # 5分钟
                'X-Cache-Status': 'hit' if metadata.get('from_cache') else 'miss',
                'X-Response-Time': str(response_time)
            }
        )
    else:
        # 代理模式：通过后端代理转发
        logger.debug(f"使用代理模式访问: {image_key}")
        return await _proxy_image_content(url, image_key, response_time)


async def _proxy_image_content(url: str, image_key: str, response_time: float):
    """
    代理转发图片内容

    Args:
        url: 图片URL
        image_key: 图片键
        response_time: 响应时间

    Returns:
        StreamingResponse: 图片流
    """
    import httpx

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # 发起请求获取图片
        response = await client.get(url)

        # 返回流式响应
        return StreamingResponse(
            content=response.iter_bytes(),
            status_code=response.status_code,
            media_type=response.headers.get('content-type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=300',
                'X-Cache-Status': 'hit',  # 代理模式总是hit
                'X-Response-Time': str(response_time),
                'X-Original-URL': url
            }
        )


@router.get(
    "/status/{image_key:path}",
    response_model=StandardResponse,
    summary="获取图片状态",
    description="检查图片URL状态、过期时间和缓存信息"
)
async def get_image_status(
    image_key: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片状态

    Args:
        image_key: 图片在COS中的存储键
        db: 数据库会话

    Returns:
        StandardResponse: 图片状态信息
    """
    handler = ImageProxyHandler(db)
    status = await handler.handle_check_url_status(image_key)

    return StandardResponse(
        status="success",
        message="获取图片状态成功",
        data=status
    )


@router.post(
    "/refresh/{image_key:path}",
    response_model=StandardResponse,
    summary="刷新图片URL",
    description="强制刷新图片的预签名URL，清除旧缓存"
)
async def refresh_image_url(
    image_key: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    刷新图片URL

    Args:
        image_key: 图片在COS中的存储键
        db: 数据库会话

    Returns:
        StandardResponse: 刷新结果
    """
    handler = ImageProxyHandler(db)
    new_url, metadata = await handler.handle_refresh_url(image_key)

    return StandardResponse(
        status="success",
        message="图片URL刷新成功",
        data={
            'image_key': image_key,
            'url': new_url,
            'metadata': metadata
        }
    )


@router.get(
    "/batch/urls",
    response_model=StandardResponse,
    summary="批量获取图片URL",
    description="批量获取多张图片的访问URL，支持并发处理"
)
async def batch_get_image_urls(
    image_keys: str = Query(..., description="图片键列表，逗号分隔"),
    refresh: bool = Query(False, description="是否强制刷新"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    max_concurrent: int = Query(10, ge=1, le=50, description="最大并发数"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量获取图片URL

    Args:
        image_keys: 图片键列表（逗号分隔）
        refresh: 是否强制刷新
        use_cache: 是否使用缓存
        max_concurrent: 最大并发数
        db: 数据库会话

    Returns:
        StandardResponse: 批量获取结果
    """
    handler = ImageProxyHandler(db)

    # 解析图片键列表
    keys_list = [key.strip() for key in image_keys.split(',') if key.strip()]

    if not keys_list:
        return StandardResponse(
            status="error",
            message="图片键列表不能为空",
            data={}
        )

    results = await handler.handle_get_multiple_urls(
        image_keys=keys_list,
        force_refresh=refresh,
        use_cache=use_cache,
        max_concurrent=max_concurrent
    )

    # 转换为响应格式
    response_data = {
        'total_requested': len(keys_list),
        'total_returned': len(results),
        'urls': {key: url for key, (url, metadata) in results.items()},
        'metadata': {key: metadata for key, (url, metadata) in results.items()}
    }

    return StandardResponse(
        status="success",
        message=f"成功获取 {len(results)}/{len(keys_list)} 个URL",
        data=response_data
    )


@router.get(
    "/stats",
    response_model=StandardResponse,
    summary="获取代理服务统计",
    description="获取图片代理服务的性能统计和缓存命中率"
)
async def get_proxy_stats(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取代理服务统计

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 统计信息
    """
    handler = ImageProxyHandler(db)
    stats = await handler.handle_get_performance_stats()

    return StandardResponse(
        status="success",
        message="获取统计信息成功",
        data=stats
    )


@router.post(
    "/cleanup",
    response_model=StandardResponse,
    summary="清理过期缓存",
    description="清理Redis中过期的图片URL缓存"
)
async def cleanup_expired_cache(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    清理过期缓存

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 清理结果
    """
    handler = ImageProxyHandler(db)
    cleaned = await handler.handle_cleanup_expired_cache()

    return StandardResponse(
        status="success",
        message=f"清理完成，共清理 {cleaned} 个过期缓存",
        data={'cleaned': cleaned}
    )


@router.post(
    "/preload",
    response_model=StandardResponse,
    summary="预加载图片URL",
    description="将图片URL预加载到缓存中，提升访问速度"
)
async def preload_image_urls(
    image_keys: str = Query(..., description="图片键列表，逗号分隔"),
    max_concurrent: int = Query(5, ge=1, le=20, description="最大并发数"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    预加载图片URL

    Args:
        image_keys: 图片键列表（逗号分隔）
        max_concurrent: 最大并发数
        db: 数据库会话

    Returns:
        StandardResponse: 预加载结果
    """
    handler = ImageProxyHandler(db)

    # 解析图片键列表
    keys_list = [key.strip() for key in image_keys.split(',') if key.strip()]

    if not keys_list:
        return StandardResponse(
            status="error",
            message="图片键列表不能为空",
            data={}
        )

    results = await handler.handle_preload_urls(
        image_keys=keys_list,
        max_concurrent=max_concurrent
    )

    success_count = sum(1 for v in results.values() if v)

    return StandardResponse(
        status="success",
        message=f"预加载完成，成功: {success_count}/{len(keys_list)}",
        data={
            'total': len(keys_list),
            'success': success_count,
            'failed': len(keys_list) - success_count,
            'results': results
        }
    )
