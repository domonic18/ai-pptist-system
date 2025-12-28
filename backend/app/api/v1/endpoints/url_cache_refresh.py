"""
URL缓存刷新API端点
处理图片URL的刷新、批量刷新和定期刷新
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.cache.url_refresh_handler import UrlRefreshHandler
from app.schemas.url_cache_refresh import (
    UrlRefreshRequest,
    BatchUrlRefreshRequest,
    ScheduleRefreshRequest,
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["URL缓存刷新"])


@router.post(
    "/refresh",
    response_model=StandardResponse,
    summary="刷新单个URL缓存",
    description="刷新单个图片的URL缓存"
)
async def refresh_single_url(
    request: UrlRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    刷新单个图片URL缓存

    Args:
        request: URL刷新请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务ID的响应
    """
    try:
        handler = UrlRefreshHandler(db)
        result = await handler.handle_refresh_single_url(request)

        logger.info(
            "URL刷新任务提交成功",
            extra={'task_id': result['task_id'], 'image_key': request.image_key}
        )

        return StandardResponse(
            status="success",
            message="URL刷新任务已提交",
            data=result
        )

    except Exception as e:
        logger.error(
            "URL刷新任务提交失败",
            extra={'image_key': request.image_key, 'error': str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL刷新失败: {str(e)}"
        ) from e


@router.post(
    "/batch-refresh",
    response_model=StandardResponse,
    summary="批量刷新URL缓存",
    description="批量刷新多个图片的URL缓存"
)
async def batch_refresh_urls(
    request: BatchUrlRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量刷新图片URL缓存

    Args:
        request: 批量刷新请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务ID的响应
    """
    try:
        handler = UrlRefreshHandler(db)
        result = await handler.handle_batch_refresh_urls(request)

        logger.info(
            "批量URL刷新任务提交成功",
            extra={'task_id': result['task_id'], 'count': result['count']}
        )

        return StandardResponse(
            status="success",
            message=f"批量刷新任务已提交: {len(request.image_keys)} 项",
            data=result
        )

    except Exception as e:
        logger.error(
            "批量URL刷新任务提交失败",
            extra={'count': len(request.image_keys), 'error': str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量刷新失败: {str(e)}"
        ) from e


@router.post(
    "/schedule",
    response_model=StandardResponse,
    summary="安排定期刷新",
    description="为图片URL设置定期刷新任务"
)
async def schedule_periodic(
    request: ScheduleRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    安排定期刷新任务

    Args:
        request: 定期刷新请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务ID的响应
    """
    try:
        handler = UrlRefreshHandler(db)
        result = await handler.handle_schedule_periodic_refresh(request)

        logger.info(
            "定期刷新任务调度成功",
            extra={
                'task_id': result['task_id'],
                'image_key': request.image_key,
                'interval': request.refresh_interval
            }
        )

        return StandardResponse(
            status="success",
            message=f"任务已调度: {request.image_key}, 间隔: {request.refresh_interval}s",
            data=result
        )

    except Exception as e:
        logger.error(
            "定期刷新任务调度失败",
            extra={'image_key': request.image_key, 'error': str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"调度刷新任务失败: {str(e)}"
        ) from e
