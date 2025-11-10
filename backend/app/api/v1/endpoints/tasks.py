"""任务管理API"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.services.tasks import (
    refresh_url_cache,
    batch_refresh_url_cache,
    schedule_periodic_refresh,
    get_active_tasks,
    get_task_result,
    get_queue_stats,
    get_cache_refresh_stats,
    revoke_task,
    TaskStatus,
)

router = APIRouter()


class RefreshRequest(BaseModel):
    """刷新请求"""
    image_key: str = Field(..., description="图片键")
    force_refresh: bool = Field(default=False, description="是否强制刷新")


class BatchRefreshRequest(BaseModel):
    """批量刷新请求"""
    image_keys: List[str] = Field(..., description="图片键列表")
    batch_size: int = Field(default=50, ge=1, le=100, description="每批处理数量")


class ScheduleRequest(BaseModel):
    """定期刷新请求"""
    image_key: str = Field(..., description="图片键")
    refresh_interval: int = Field(default=3600, ge=60, description="刷新间隔（秒）")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


class ActiveTaskResponse(BaseModel):
    """活跃任务响应"""
    task_id: str
    name: str
    status: str
    worker: Optional[str] = None
    start_time: Optional[datetime] = None
    eta: Optional[datetime] = None


class QueueStatsResponse(BaseModel):
    """队列统计响应"""
    total_workers: int
    active_tasks: int
    scheduled_tasks: int
    reserved_tasks: int
    workers: List[Dict[str, Any]]
    timestamp: datetime


@router.post(
    "/refresh",
    response_model=TaskResponse,
    summary="刷新单个URL缓存",
)
async def refresh_single_url(request: RefreshRequest):
    """刷新单个图片URL缓存"""
    try:
        task = refresh_url_cache.apply_async(args=[request.image_key], kwargs={"force_refresh": request.force_refresh})

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Task submitted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch-refresh",
    response_model=TaskResponse,
    summary="批量刷新URL缓存",
)
async def batch_refresh_urls(request: BatchRefreshRequest):
    """批量刷新多个图片URL缓存"""
    try:
        task = batch_refresh_url_cache.apply_async(
            args=[request.image_keys],
            kwargs={
                "batch_size": request.batch_size,
            }
        )

        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message=f"Batch refresh task submitted: {len(request.image_keys)} items",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/schedule",
    response_model=TaskResponse,
    summary="安排定期刷新",
)
async def schedule_periodic(request: ScheduleRequest):
    """安排定期刷新任务"""
    try:
        task_id = schedule_periodic_refresh(request.image_key, request.refresh_interval)

        return TaskResponse(
            task_id=task_id,
            status="SCHEDULED",
            message=f"Task scheduled for {request.image_key}, interval: {request.refresh_interval}s",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/active",
    response_model=List[ActiveTaskResponse],
    summary="获取活跃任务",
)
async def list_active_tasks():
    """获取当前活跃的任务列表"""
    try:
        tasks = get_active_tasks()

        # 转换时间格式
        response_tasks = []
        for task in tasks:
            start_time = None
            eta = None

            if task.get("start_time"):
                # Celery返回的start_time是时间戳
                start_time = datetime.utcfromtimestamp(task["start_time"])

            if task.get("eta"):
                # 转换ISO时间字符串
                eta = datetime.fromisoformat(task["eta"])

            response_tasks.append(
                ActiveTaskResponse(
                    task_id=task["task_id"],
                    name=task["name"],
                    status=task["status"],
                    worker=task.get("worker"),
                    start_time=start_time,
                    eta=eta,
                )
            )

        return response_tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status/{task_id}",
    summary="获取任务状态",
)
async def get_status(task_id: str):
    """获取指定任务的状态和结果"""
    try:
        result = get_task_result(task_id)

        if not result:
            raise HTTPException(status_code=404, detail="Task not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/queue/stats",
    response_model=QueueStatsResponse,
    summary="获取队列统计",
)
async def get_queue_statistics():
    """获取任务队列统计信息"""
    try:
        stats = get_queue_stats()
        stats["timestamp"] = datetime.utcnow()

        return QueueStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cache/stats",
    summary="获取缓存刷新统计",
)
async def get_cache_statistics():
    """获取缓存刷新统计信息"""
    try:
        stats = get_cache_refresh_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/revoke/{task_id}",
    summary="撤销任务",
)
async def revoke_task_endpoint(
    task_id: str,
    terminate: bool = Query(default=False, description="是否强制终止"),
):
    """撤销指定任务"""
    try:
        success = revoke_task(task_id, terminate=terminate)

        if success:
            return {"message": f"Task {task_id} revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found or cannot be revoked")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    summary="健康检查",
)
async def health_check():
    """检查任务系统健康状态"""
    try:
        stats = get_queue_stats()

        # 简单的健康检查：至少有1个工作节点
        if stats["total_workers"] == 0:
            return {
                "status": "unhealthy",
                "message": "No active workers",
                "workers": 0,
            }

        return {
            "status": "healthy",
            "message": "Task system is running normally",
            "workers": stats["total_workers"],
            "active_tasks": stats["active_tasks"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
        }
