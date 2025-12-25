"""
图片编辑 Celery 任务
负责将混合OCR识别和图片编辑任务异步化执行
"""

from typing import Dict, Any
from celery import Task

from app.services.tasks.celery_app import celery_app
from app.core.log_utils import get_logger
from app.models.image_editing_task import EditingTaskStatus
from app.utils.async_utils import AsyncRunner

logger = get_logger(__name__)


# ============================================================================
# 混合OCR识别任务
# ============================================================================

@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    time_limit=300,  # 5分钟超时
    soft_time_limit=270,
    queue='image_editing'
)
def hybrid_ocr_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    混合OCR识别的 Celery 任务

    Args:
        task_id: 任务ID
        slide_id: 幻灯片ID
        cos_key: 图片COS Key
        user_id: 用户ID（可选）

    Returns:
        识别结果字典
    """
    logger.info("开始混合OCR识别任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_hybrid_ocr(
            task_id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id
        )
    except Exception as exc:
        return _handle_editing_error(
            self=self,
            task_id=task_id,
            slide_id=slide_id,
            error=exc
        )


def _execute_hybrid_ocr(
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    执行混合OCR识别的核心逻辑

    将异步操作封装在 AsyncRunner 中统一管理
    """
    from app.db.database import AsyncSessionLocal
    from app.services.editing.image_editing_service import ImageEditingService

    with AsyncRunner() as runner:
        async def do_ocr():
            # 使用数据库会话执行OCR识别
            async with AsyncSessionLocal() as db:
                service = ImageEditingService(db)

                # 执行混合OCR识别
                result = await service.parse_with_hybrid_ocr(
                    slide_id=slide_id,
                    cos_key=cos_key,
                    user_id=user_id,
                    task_id=task_id
                )

                return result

        result = runner.run(do_ocr())

        logger.info("混合OCR识别完成", extra={
            "task_id": task_id,
            "slide_id": slide_id,
            "text_count": len(result.text_regions) if result.text_regions else 0
        })

        return {
            "task_id": task_id,
            "slide_id": slide_id,
            "cos_key": cos_key,
            "status": "completed",
            "progress": 50,  # OCR完成，进度50%
            "parse_time_ms": result.metadata.parse_time_ms if result.metadata else 0,
            "text_count": len(result.text_regions) if result.text_regions else 0
        }


def _handle_editing_error(
    self: Task,
    task_id: str,
    slide_id: str,
    error: Exception
) -> Dict[str, Any]:
    """
    处理编辑失败的情况

    如果还有重试次数，则重试；否则标记为失败
    """
    logger.error("图片编辑任务失败", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "error": str(error),
        "retry_count": self.request.retries
    })

    # 标记任务失败状态到数据库
    _mark_task_as_failed(task_id, slide_id, error)

    # 还有重试次数，触发重试
    if self.request.retries < self.max_retries:
        countdown = 5 * (2 ** self.request.retries)  # 指数退避
        raise self.retry(exc=error, countdown=countdown)

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
        from app.repositories.image_editing import ImageEditingRepository
        from app.models.image_editing_task import EditingTaskStatus
        from app.utils.async_utils import run_async

        async def update_failed_status():
            async with AsyncSessionLocal() as db:
                repo = ImageEditingRepository(db)
                await repo.update_task_status(
                    task_id=task_id,
                    status=EditingTaskStatus.FAILED,
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


# ============================================================================
# 完整编辑任务（OCR + 文字去除）
# ============================================================================

@celery_app.task(
    bind=True,
    max_retries=2,
    retry_backoff=True,
    time_limit=600,  # 10分钟超时
    soft_time_limit=540,
    queue='image_editing'
)
def full_editing_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    完整图片编辑的 Celery 任务

    包含混合OCR识别和文字去除两个步骤

    Args:
        task_id: 任务ID
        slide_id: 幻灯片ID
        cos_key: 图片COS Key
        user_id: 用户ID（可选）

    Returns:
        编辑结果字典
    """
    logger.info("开始完整图片编辑任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_full_editing(
            task_id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id
        )
    except Exception as exc:
        return _handle_editing_error(
            self=self,
            task_id=task_id,
            slide_id=slide_id,
            error=exc
        )


def _execute_full_editing(
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    执行完整图片编辑的核心逻辑

    1. 混合OCR识别
    2. 文字去除（第二阶段实现）
    """
    from app.db.database import AsyncSessionLocal
    from app.services.editing.image_editing_service import ImageEditingService

    with AsyncRunner() as runner:
        async def do_editing():
            # 使用数据库会话执行编辑
            async with AsyncSessionLocal() as db:
                service = ImageEditingService(db)

                # 步骤1: 执行混合OCR识别
                logger.info("步骤1: 开始混合OCR识别", extra={"task_id": task_id})
                ocr_result = await service.parse_with_hybrid_ocr(
                    slide_id=slide_id,
                    cos_key=cos_key,
                    user_id=user_id,
                    task_id=task_id
                )

                # 步骤2: 文字去除（第二阶段实现）
                # 目前暂时跳过，直接返回OCR结果
                logger.info("步骤2: 文字去除功能待实现", extra={"task_id": task_id})

                return ocr_result

        result = runner.run(do_editing())

        logger.info("完整图片编辑完成", extra={
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
            "text_count": len(result.text_regions) if result.text_regions else 0,
            "note": "文字去除功能待第二阶段实现"
        }
