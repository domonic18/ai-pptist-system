"""Celery应用配置"""

import os
from pathlib import Path
from celery import Celery
from kombu import Queue
from app.core.config import settings

# 创建Celery应用
# 使用不同的Redis数据库索引：db 0 for broker, db 1 for result backend
celery_app = Celery(
    "ai_pptist_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=[
        "app.services.tasks.refresh_tasks",
    ],
)

# Celery配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # 任务执行配置
    task_always_eager=False,  # 设置为False以启用异步执行
    task_eager_propagate=True,  # 异常传播
    task_ignore_result=False,  # 保存结果
    task_store_eager_result=False,  # 避免重复计算

    # 重试配置
    task_acks_late=True,  # 任务确认延迟
    worker_prefetch_multiplier=1,  # 工作者预取因子

    # 路由配置
    task_routes={
        "app.services.tasks.refresh_tasks.refresh_url_cache": {"queue": "quick"},
        "app.services.tasks.refresh_tasks.batch_refresh_url_cache": {"queue": "batch"},
        "app.services.tasks.refresh_tasks.cleanup_expired_cache": {"queue": "maintenance"},
        "app.services.tasks.refresh_tasks.pre_refresh_active_urls": {"queue": "maintenance"},
    },

    # 队列配置
    task_default_queue="default",
    task_queues=(
        Queue("quick", routing_key="quick"),
        Queue("batch", routing_key="batch"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("default", routing_key="default"),
    ),

    # 定期任务
    beat_schedule={
        "refresh-expired-urls-every-hour": {
            "task": "app.services.tasks.refresh_tasks.cleanup_expired_cache",
            "schedule": 3600.0,  # 每小时执行
            "options": {"queue": "maintenance"},
        },
        "pre-refresh-urls-every-15-min": {
            "task": "app.services.tasks.refresh_tasks.pre_refresh_active_urls",
            "schedule": 900.0,  # 每15分钟执行
            "options": {"queue": "maintenance"},
        },
    },
    # 将celerybeat-schedule文件存储在workspace目录
    beat_schedule_filename=str(Path(settings.workspace_dir) / "celerybeat-schedule"),
)


def init_celery() -> Celery:
    """初始化Celery应用（用于依赖注入）"""
    return celery_app
