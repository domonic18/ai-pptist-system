"""Celery集成配置"""

import logging
import asyncio
from typing import Optional
from celery import Celery
from fastapi import FastAPI

from app.services.tasks import (
    celery_app,
    init_celery,
    get_queue_stats,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class CeleryManager:
    """Celery管理器"""

    def __init__(self):
        self._app: Optional[Celery] = None
        self._is_running = False

    def init_app(self, app: FastAPI) -> None:
        """初始化Celery（适配FastAPI生命周期）"""
        self._app = init_celery()

        @app.on_event("startup")
        async def startup_event():
            """应用启动时执行"""
            await self.start()

        @app.on_event("shutdown")
        async def shutdown_event():
            """应用关闭时执行"""
            await self.stop()

    async def start(self) -> None:
        """启动Celery工作者（可选：仅在单实例部署时使用）"""
        if self._is_running:
            return

        try:
            # 注意：通常不会在应用进程内启动工作者
            # 这里仅记录配置信息
            logger.info(
                "Celery configured. Use the following command to start workers:\n"
                "  celery -A app.services.tasks worker --loglevel=info "
                "-Q banana,quick,batch,maintenance,default"
            )
            logger.info("Celery queues: banana, quick, batch, maintenance, default")
            self._is_running = True
        except Exception as e:
            logger.error(f"Failed to initialize Celery: {e}")
            raise

    async def stop(self) -> None:
        """停止Celery"""
        if not self._is_running:
            return

        logger.info("Celery shutdown")
        self._is_running = False

    async def get_status(self) -> dict:
        """获取Celery状态"""
        return {
            "status": "running" if self._is_running else "stopped",
            "queues": ["banana", "quick", "batch", "maintenance", "default"],
            "broker_url": self._app.conf.broker_url if self._app else None,
            "backend_url": self._app.conf.result_backend if self._app else None,
        }


# 全局Celery管理器实例
celery_manager = CeleryManager()


# 便捷函数：检查任务状态
def check_celery_health() -> dict:
    """检查Celery健康状态"""
    try:
        stats = get_queue_stats()
        return {
            "status": "healthy",
            "workers": stats["total_workers"],
            "active_tasks": stats["active_tasks"],
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
