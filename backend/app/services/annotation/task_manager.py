"""
标注任务管理器

职责:
- 任务状态管理
- 进度追踪
- Redis数据持久化
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.core.log_utils import get_logger

logger = get_logger(__name__)


class TaskManager:
    """标注任务管理器"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    def set_redis_client(self, redis_client):
        """设置Redis客户端"""
        self.redis_client = redis_client

    async def create_task(
        self,
        task_id: str,
        user_id: str,
        slide_count: int,
        model_config: Dict[str, Any],
        extraction_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建任务记录

        Args:
            task_id: 任务ID
            user_id: 用户ID
            slide_count: 幻灯片数量
            model_config: 模型配置
            extraction_config: 提取配置

        Returns:
            Dict[str, Any]: 任务数据
        """
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "pending",
            "total_pages": slide_count,
            "completed_pages": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_config": model_config,
            "extraction_config": extraction_config
        }

        await self.redis_client.set(
            f"annotation:task:{task_id}",
            json.dumps(task_data),
            expire=3600  # 1小时过期
        )

        return task_data

    async def update_task_status(self, task_id: str, status: str):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
        """
        task_data_str = await self.redis_client.get(f"annotation:task:{task_id}")
        if task_data_str:
            task_data = json.loads(task_data_str)
            task_data["status"] = status
            task_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self.redis_client.set(
                f"annotation:task:{task_id}",
                json.dumps(task_data),
                expire=3600
            )

    async def update_task_progress(
        self,
        task_id: str,
        completed: int,
        total: int
    ):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            completed: 已完成数量
            total: 总数
        """
        task_data_str = await self.redis_client.get(f"annotation:task:{task_id}")
        if task_data_str:
            task_data = json.loads(task_data_str)
            task_data["completed_pages"] = completed
            task_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self.redis_client.set(
                f"annotation:task:{task_id}",
                json.dumps(task_data),
                expire=3600
            )

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务数据

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 任务数据

        Raises:
            ValueError: 任务不存在
        """
        task_data_str = await self.redis_client.get(f"annotation:task:{task_id}")
        if not task_data_str:
            raise ValueError(f"任务不存在: {task_id}")

        return json.loads(task_data_str)

    async def save_results(self, task_id: str, results: List[Dict[str, Any]]):
        """
        保存标注结果

        Args:
            task_id: 任务ID
            results: 结果列表
        """
        await self.redis_client.set(
            f"annotation:results:{task_id}",
            json.dumps(results),
            expire=3600
        )

    async def get_results(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取标注结果

        Args:
            task_id: 任务ID

        Returns:
            List[Dict[str, Any]]: 结果列表

        Raises:
            ValueError: 结果不存在
        """
        results_str = await self.redis_client.get(f"annotation:results:{task_id}")
        if not results_str:
            raise ValueError(f"结果不存在: {task_id}")

        return json.loads(results_str)
