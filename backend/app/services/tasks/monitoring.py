"""任务监控和状态查询"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from celery.result import AsyncResult
from celery.app.control import Inspect

from .celery_app import celery_app

logger = logging.getLogger(__name__)


class TaskStatus:
    """任务状态常量"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


def get_active_tasks() -> List[Dict[str, Any]]:
    """获取活跃任务列表

    Returns:
        活跃任务列表
    """
    inspect = celery_app.control.inspect()

    # 获取运行中的任务
    active_tasks = inspect.active() or {}

    # 获取已调度的任务
    scheduled_tasks = inspect.scheduled() or {}

    tasks = []

    for worker, task_list in active_tasks.items():
        for task in task_list:
            tasks.append(
                {
                    "task_id": task["id"],
                    "name": task["name"],
                    "args": task["args"],
                    "kwargs": task["kwargs"],
                    "status": TaskStatus.STARTED,
                    "worker": worker,
                    "start_time": task["time_start"],
                    "hostname": task["hostname"],
                }
            )

    for worker, task_list in scheduled_tasks.items():
        for task in task_list:
            tasks.append(
                {
                    "task_id": task["id"],
                    "name": task["name"],
                    "args": task["args"],
                    "kwargs": task["kwargs"],
                    "status": TaskStatus.PENDING,
                    "worker": worker,
                    "eta": task["eta"],
                    "hostname": task["hostname"],
                }
            )

    return tasks


def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务结果

    Args:
        task_id: 任务ID

    Returns:
        任务结果
    """
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": result.id,
        "status": result.status,
        "result": None,
        "traceback": None,
        "date_done": result.date_done.isoformat() if result.date_done else None,
        "successful": result.successful() if result.ready() else None,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["traceback"] = result.traceback
            response["error"] = str(result.info) if result.info else "Unknown error"

    return response


def get_queue_stats() -> Dict[str, Any]:
    """获取队列统计信息

    Returns:
        队列统计信息
    """
    inspect = celery_app.control.inspect()

    # 工作节点状态
    stats = inspect.stats() or {}

    # 活跃任务数
    active = inspect.active() or {}
    active_count = sum(len(tasks) for tasks in active.values())

    # 等待任务数
    scheduled = inspect.scheduled() or {}
    scheduled_count = sum(len(tasks) for tasks in scheduled.values())

    # 保留任务数
    reserved = inspect.reserved() or {}
    reserved_count = sum(len(tasks) for tasks in reserved.values())

    # 统计每个工作节点
    workers = []
    for worker_name, worker_stats in stats.items():
        worker_active = len(active.get(worker_name, []))
        worker_scheduled = len(scheduled.get(worker_name, []))
        worker_reserved = len(reserved.get(worker_name, []))

        workers.append(
            {
                "name": worker_name,
                "status": "online" if worker_stats else "offline",
                "active_tasks": worker_active,
                "scheduled_tasks": worker_scheduled,
                "reserved_tasks": worker_reserved,
                "load_average": worker_stats.get("loadavg", []),
                "pid": worker_stats.get("pid"),
            }
        )

    return {
        "total_workers": len(stats),
        "active_tasks": active_count,
        "scheduled_tasks": scheduled_count,
        "reserved_tasks": reserved_count,
        "workers": workers,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_task_history(
    hours: int = 24,
    task_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """获取任务历史记录

    Args:
        hours: 查询过去多少小时的任务
        task_name: 任务名称过滤

    Returns:
        任务历史记录列表
    """
    from app.core.cache.redis import redis_client

    try:
        # 简化任务历史查询 - 通过Celery内置方法
        from celery.task.control import inspect

        i = inspect()
        stats = i.stats()

        if not stats:
            return []

        # 获取最近的任务
        history = []
        # 这里简化处理，实际生产中应使用专用数据库存储任务历史
        return history

    except Exception as e:
        logger.error(f"Failed to get task history: {e}")
        return []


def get_cache_refresh_stats() -> Dict[str, Any]:
    """获取缓存刷新统计信息

    Returns:
        缓存刷新统计
    """
    from app.utils.imageErrorHandler import get_error_stats
    from app.services.cache.url_cache import ImageURLCache

    try:
        # 获取错误统计
        error_stats = get_error_stats()

        # 获取缓存统计
        cache = ImageURLCache()
        cache_stats = cache.get_stats()

        return {
            "error_stats": error_stats,
            "cache_stats": cache_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get cache refresh stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """撤销任务

    Args:
        task_id: 任务ID
        terminate: 是否强制终止

    Returns:
        是否成功撤销
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        logger.info(f"Task {task_id} revoked successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to revoke task {task_id}: {e}")
        return False
