"""任务队列系统

基于Celery实现图片URL的定时刷新、批量刷新、PPT生成和任务监控。
"""

from celery_app import celery_app, init_celery
from .refresh_tasks import (
    refresh_url_cache,
    batch_refresh_url_cache,
    schedule_periodic_refresh,
)
from .banana_generation_tasks import (
    generate_single_slide_task,
    generate_batch_slides_task,
)
from .monitoring import (
    get_active_tasks,
    get_task_result,
    get_queue_stats,
    get_cache_refresh_stats,
    revoke_task,
    TaskStatus,
)

__all__ = [
    "celery_app",
    "init_celery",
    "refresh_url_cache",
    "batch_refresh_url_cache",
    "schedule_periodic_refresh",
    "generate_single_slide_task",
    "generate_batch_slides_task",
    "get_active_tasks",
    "get_task_result",
    "get_queue_stats",
    "get_cache_refresh_stats",
    "revoke_task",
    "TaskStatus",
]
