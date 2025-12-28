"""
Celery队列管理API端点
处理Celery任务队列的监控、查询和管理
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.cache.celery_queue_handler import CeleryQueueHandler
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Celery队列管理"])


@router.get(
    "/active",
    response_model=StandardResponse,
    summary="获取活跃任务",
    description="获取当前活跃的任务列表"
)
async def list_active_tasks(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取活跃任务列表

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 包含活跃任务列表的响应
    """
    try:
        handler = CeleryQueueHandler(db)
        tasks = await handler.handle_list_active_tasks()

        logger.info(f"获取到 {len(tasks)} 个活跃任务")

        return StandardResponse(
            status="success",
            message=f"获取到 {len(tasks)} 个活跃任务",
            data={"tasks": tasks}
        )

    except Exception as e:
        logger.error("获取活跃任务失败", extra={'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取活跃任务失败: {str(e)}"
        ) from e


@router.get(
    "/status/{task_id}",
    response_model=StandardResponse,
    summary="获取任务状态",
    description="获取指定任务的状态和结果"
)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取任务状态

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务状态的响应
    """
    try:
        handler = CeleryQueueHandler(db)
        result = await handler.handle_get_task_status(task_id)

        logger.info("获取任务状态成功", extra={'task_id': task_id})

        return StandardResponse(
            status="success",
            message="获取任务状态成功",
            data=result
        )

    except ValueError as e:
        logger.warning("任务不存在", extra={'task_id': task_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        ) from e
    except Exception as e:
        logger.error("获取任务状态失败", extra={'task_id': task_id, 'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        ) from e


@router.get(
    "/queue/stats",
    response_model=StandardResponse,
    summary="获取队列统计",
    description="获取任务队列统计信息"
)
async def get_queue_statistics(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取队列统计信息

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 包含队列统计的响应
    """
    try:
        handler = CeleryQueueHandler(db)
        stats = await handler.handle_get_queue_stats()

        logger.info(
            "获取队列统计成功",
            extra={
                'total_workers': stats["total_workers"],
                'active_tasks': stats["active_tasks"]
            }
        )

        return StandardResponse(
            status="success",
            message="获取队列统计成功",
            data=stats
        )

    except Exception as e:
        logger.error("获取队列统计失败", extra={'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取队列统计失败: {str(e)}"
        ) from e


@router.get(
    "/cache/stats",
    response_model=StandardResponse,
    summary="获取缓存统计",
    description="获取URL缓存刷新统计信息"
)
async def get_cache_statistics(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取缓存统计信息

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 包含缓存统计的响应
    """
    try:
        handler = CeleryQueueHandler(db)
        stats = await handler.handle_get_cache_stats()

        logger.info("获取缓存统计成功")

        return StandardResponse(
            status="success",
            message="获取缓存统计成功",
            data=stats
        )

    except Exception as e:
        logger.error("获取缓存统计失败", extra={'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取缓存统计失败: {str(e)}"
        ) from e


@router.delete(
    "/revoke/{task_id}",
    response_model=StandardResponse,
    summary="撤销任务",
    description="撤销指定的任务"
)
async def revoke_task_endpoint(
    task_id: str,
    terminate: bool = Query(default=False, description="是否强制终止"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    撤销任务

    Args:
        task_id: 任务ID
        terminate: 是否强制终止
        db: 数据库会话

    Returns:
        StandardResponse: 撤销结果
    """
    try:
        handler = CeleryQueueHandler(db)
        result = await handler.handle_revoke_task(task_id, terminate)

        logger.info("任务撤销成功", extra={'task_id': task_id, 'terminate': terminate})

        return StandardResponse(
            status="success",
            message=f"任务 {task_id} 已成功撤销",
            data=result
        )

    except ValueError as e:
        logger.warning("任务不存在或无法撤销", extra={'task_id': task_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无法撤销"
        ) from e
    except Exception as e:
        logger.error("撤销任务失败", extra={'task_id': task_id, 'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"撤销任务失败: {str(e)}"
        ) from e


@router.get(
    "/health",
    response_model=StandardResponse,
    summary="健康检查",
    description="检查任务系统健康状态"
)
async def health_check(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    健康检查

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 健康状态
    """
    try:
        handler = CeleryQueueHandler(db)
        result = await handler.handle_health_check()

        if result["status"] == "healthy":
            logger.info("健康检查通过", extra={'workers': result.get('workers')})
        else:
            logger.warning("健康检查失败", extra={'message': result['message']})

        return StandardResponse(
            status="success" if result["status"] == "healthy" else "error",
            message=result["message"],
            data=result
        )

    except Exception as e:
        logger.error("健康检查失败", extra={'error': str(e)})
        return StandardResponse(
            status="error",
            message=f"健康检查失败: {str(e)}",
            data={"status": "unhealthy"}
        )
