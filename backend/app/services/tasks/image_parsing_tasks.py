"""
图片解析 Celery 任务

负责将图片OCR识别任务异步化执行
"""

from typing import Dict, Any
from celery import Task

from app.services.tasks.celery_app import celery_app
from app.core.log_utils import get_logger
from app.models.image_parse_task import ParseTaskStatus
from app.utils.async_utils import AsyncRunner

logger = get_logger(__name__)


# ============================================================================
# 图片解析任务
# ============================================================================

@celery_app.task(
    bind=True,
    time_limit=300,  # 5分钟超时
    soft_time_limit=270,
    queue='image_parsing'
)
def parse_image_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    图片OCR识别的 Celery 任务

    Args:
        task_id: 任务ID
        slide_id: 幻灯片ID
        cos_key: 图片COS Key
        user_id: 用户ID（可选）

    Returns:
        解析结果字典
    """
    logger.info("开始图片解析任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_image_parsing(
            task_id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id
        )
    except Exception as exc:
        return _handle_parsing_error(
            self=self,
            task_id=task_id,
            slide_id=slide_id,
            error=exc
        )


def _execute_image_parsing(
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    执行图片OCR识别的核心逻辑

    将异步操作封装在 AsyncRunner 中统一管理
    """
    from app.core.cache.redis import get_redis
    from app.db.database import AsyncSessionLocal
    from app.services.parsing.image_parsing.service import ImageParsingService

    with AsyncRunner() as runner:
        async def do_parsing():
            # 1. 初始化 Redis
            redis_client = await get_redis()

            # 2. 使用数据库会话执行OCR识别
            async with AsyncSessionLocal() as db:
                service = ImageParsingService(db)

                # 执行图片解析（传入task_id以使用API创建的任务记录）
                result = await service.parse_image(
                    slide_id=slide_id,
                    cos_key=cos_key,
                    user_id=user_id,
                    task_id=task_id
                )

                # 确保所有数据库更改已提交
                await db.commit()

                return result, redis_client

        result, redis_client = runner.run(do_parsing())

        logger.info("图片解析完成", extra={
            "task_id": task_id,
            "slide_id": slide_id,
            "text_count": len(result.text_regions) if result.text_regions else 0
        })

        return {
            "task_id": task_id,
            "slide_id": slide_id,
            "cos_key": cos_key,
            "status": "completed",
            "progress": 100,
            "parse_time": result.metadata.parse_time if result.metadata else 0,
            "text_count": len(result.text_regions) if result.text_regions else 0
        }


def _handle_parsing_error(
    self: Task,
    task_id: str,
    slide_id: str,
    error: Exception
) -> Dict[str, Any]:
    """
    处理解析失败的情况

    标记任务为失败状态，不进行重试
    """
    logger.error("图片解析失败", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "error": str(error)
    })

    # 标记任务失败状态到数据库
    _mark_task_as_failed(task_id, slide_id, error)

    return {
        "task_id": task_id,
        "slide_id": slide_id,
        "status": "failed",
        "error": str(error)
    }


def _mark_task_as_failed(task_id: str, slide_id: str, error: Exception):
    """在数据库中标记任务失败状态"""
    try:
        from app.db.database import AsyncSessionLocal
        from app.repositories.image_parsing import ImageParsingRepository
        from app.utils.async_utils import run_async

        async def update_failed_status():
            async with AsyncSessionLocal() as db:
                repo = ImageParsingRepository(db)
                await repo.update_task_status(
                    task_id=task_id,
                    status=ParseTaskStatus.FAILED,
                    error_message=str(error)
                )
                await db.commit()

        run_async(update_failed_status())

    except Exception as update_exc:
        logger.error("标记失败状态失败", extra={
            "task_id": task_id,
            "slide_id": slide_id,
            "update_error": str(update_exc)
        })
