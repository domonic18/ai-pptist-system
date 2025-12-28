"""
Celery队列管理处理器
处理Celery任务队列监控和管理的业务逻辑
"""

from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tasks import (
    get_active_tasks,
    get_task_result,
    get_queue_stats,
    get_cache_refresh_stats,
    revoke_task,
    TaskStatus,
)
from app.schemas.celery_queue import (
    ActiveTaskResponse,
    QueueStatsResponse,
    HealthCheckResponse,
    CacheStatsResponse,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class CeleryQueueHandler:
    """Celery队列管理处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_list_active_tasks(self) -> List[Dict[str, Any]]:
        """
        处理获取活跃任务列表

        Returns:
            活跃任务列表
        """
        logger.info("获取活跃任务列表")

        tasks = get_active_tasks()

        # 转换时间格式
        response_tasks = []
        for task in tasks:
            start_time = None
            eta = None

            if task.get("start_time"):
                start_time = datetime.utcfromtimestamp(task["start_time"])

            if task.get("eta"):
                eta = datetime.fromisoformat(task["eta"])

            response_tasks.append({
                "task_id": task["task_id"],
                "name": task["name"],
                "status": task["status"],
                "worker": task.get("worker"),
                "start_time": start_time,
                "eta": eta,
            })

        logger.info(f"获取到 {len(response_tasks)} 个活跃任务")

        return response_tasks

    async def handle_get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        处理获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        logger.info("获取任务状态", extra={'task_id': task_id})

        result = get_task_result(task_id)

        if not result:
            logger.warning("任务不存在", extra={'task_id': task_id})
            raise ValueError("Task not found")

        logger.info(
            "获取任务状态成功",
            extra={'task_id': task_id, 'status': result.get('status')}
        )

        return result

    async def handle_get_queue_stats(self) -> Dict[str, Any]:
        """
        处理获取队列统计信息

        Returns:
            队列统计信息
        """
        logger.info("获取队列统计信息")

        stats = get_queue_stats()
        stats["timestamp"] = datetime.utcnow()

        logger.info(
            "获取队列统计成功",
            extra={
                'total_workers': stats["total_workers"],
                'active_tasks': stats["active_tasks"]
            }
        )

        return stats

    async def handle_get_cache_stats(self) -> Dict[str, Any]:
        """
        处理获取缓存统计信息

        Returns:
            缓存统计信息
        """
        logger.info("获取缓存统计信息")

        stats = get_cache_refresh_stats()

        logger.info(
            "获取缓存统计成功",
            extra={'total_cached': stats.get('total_cached', 0)}
        )

        return stats

    async def handle_revoke_task(
        self,
        task_id: str,
        terminate: bool = False
    ) -> Dict[str, Any]:
        """
        处理撤销任务

        Args:
            task_id: 任务ID
            terminate: 是否强制终止

        Returns:
            撤销结果
        """
        logger.info(
            "撤销任务",
            extra={'task_id': task_id, 'terminate': terminate}
        )

        success = revoke_task(task_id, terminate=terminate)

        if not success:
            logger.warning("任务不存在或无法撤销", extra={'task_id': task_id})
            raise ValueError("Task not found or cannot be revoked")

        logger.info("任务撤销成功", extra={'task_id': task_id})

        return {
            "task_id": task_id,
            "success": True,
            "message": f"Task {task_id} revoked successfully"
        }

    async def handle_health_check(self) -> Dict[str, Any]:
        """
        处理健康检查

        Returns:
            健康状态信息
        """
        logger.info("执行健康检查")

        stats = get_queue_stats()

        # 简单的健康检查：至少有1个工作节点
        if stats["total_workers"] == 0:
            logger.warning("健康检查失败：无活跃工作节点")
            return {
                "status": "unhealthy",
                "message": "No active workers",
                "workers": 0,
            }

        logger.info(
            "健康检查通过",
            extra={
                'workers': stats["total_workers"],
                'active_tasks': stats["active_tasks"]
            }
        )

        return {
            "status": "healthy",
            "message": "Task system is running normally",
            "workers": stats["total_workers"],
            "active_tasks": stats["active_tasks"],
        }
