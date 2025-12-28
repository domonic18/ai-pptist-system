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
    from app.services.editing.image_editing.service import ImageEditingService

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

    标记任务为失败状态，不进行重试
    """
    logger.error("图片编辑任务失败", extra={
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
    time_limit=600,  # 10分钟超时
    soft_time_limit=540,
    queue='image_editing'
)
def full_editing_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None,
    ai_model_id: str = None
) -> Dict[str, Any]:
    """
    完整图片编辑的 Celery 任务

    包含混合OCR识别和文字去除两个步骤

    Args:
        task_id: 任务ID
        slide_id: 幻灯片ID
        cos_key: 图片COS Key
        user_id: 用户ID（可选）
        ai_model_id: AI模型ID（可选，用于文字去除）

    Returns:
        编辑结果字典
    """
    logger.info("开始完整图片编辑任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key,
        "ai_model_id": ai_model_id,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_full_editing(
            task_id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id,
            ai_model_id=ai_model_id
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
    user_id: str = None,
    ai_model_id: str = None
) -> Dict[str, Any]:
    """
    执行完整图片编辑的核心逻辑

    1. 混合OCR识别
    2. 文字去除
    """
    from app.db.database import AsyncSessionLocal
    from app.services.editing.image_editing.service import ImageEditingService

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

                # 步骤2: 文字去除
                logger.info("步骤2: 开始文字去除", extra={"task_id": task_id, "ai_model_id": ai_model_id})
                removal_result = await service.remove_text_from_image(
                    slide_id=slide_id,
                    cos_key=cos_key,
                    ai_model_id=ai_model_id,
                    user_id=user_id,
                    task_id=task_id,
                    ocr_result=ocr_result
                )

                # 返回完整结果
                return {
                    "ocr_result": ocr_result,
                    "removal_result": removal_result
                }

        result = runner.run(do_editing())

        logger.info("完整图片编辑完成", extra={
            "task_id": task_id,
            "slide_id": slide_id,
            "text_count": len(result.get("ocr_result", {}).text_regions) if result.get("ocr_result") else 0,
            "edited_cos_key": result.get("removal_result", {}).get("edited_cos_key")
        })

        return {
            "task_id": task_id,
            "slide_id": slide_id,
            "cos_key": cos_key,
            "status": "completed",
            "progress": 100,
            "text_count": len(result.get("ocr_result", {}).text_regions) if result.get("ocr_result") else 0,
            "edited_cos_key": result.get("removal_result", {}).get("edited_cos_key")
        }


# ============================================================================
# MinerU识别任务
# ============================================================================

@celery_app.task(
    bind=True,
    time_limit=600,  # 10分钟超时
    soft_time_limit=540,
    queue='image_editing'
)
def mineru_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None,
    enable_formula: bool = True,
    enable_table: bool = True,
    enable_style_recognition: bool = True,
    remove_text: bool = False
) -> Dict[str, Any]:
    """
    MinerU识别的 Celery 任务

    使用MinerU进行高精度文字识别，可选择是否去除文字

    Args:
        task_id: 任务ID
        slide_id: 幻灯片ID
        cos_key: 图片COS Key
        user_id: 用户ID（可选）
        enable_formula: 是否识别公式
        enable_table: 是否识别表格
        enable_style_recognition: 是否启用样式识别
        remove_text: 是否去除文字

    Returns:
        识别结果字典
    """
    logger.info("开始MinerU识别任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
        "enable_style_recognition": enable_style_recognition,
        "remove_text": remove_text,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_mineru_recognition(
            task_id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id,
            enable_formula=enable_formula,
            enable_table=enable_table,
            enable_style_recognition=enable_style_recognition,
            remove_text=remove_text
        )
    except Exception as exc:
        return _handle_editing_error(
            self=self,
            task_id=task_id,
            slide_id=slide_id,
            error=exc
        )


def _execute_mineru_recognition(
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None,
    enable_formula: bool = True,
    enable_table: bool = True,
    enable_style_recognition: bool = True,
    remove_text: bool = False
) -> Dict[str, Any]:
    """
    执行MinerU识别的核心逻辑

    1. MinerU识别（获取精确坐标）
    2. 可选：文字去除
    """
    from app.db.database import AsyncSessionLocal
    from app.services.editing.image_editing.service import ImageEditingService

    with AsyncRunner() as runner:
        async def do_recognition():
            # 使用数据库会话执行识别
            async with AsyncSessionLocal() as db:
                service = ImageEditingService(db)

                # 步骤1: 执行MinerU识别
                logger.info("步骤1: 开始MinerU识别", extra={"task_id": task_id})
                ocr_result = await service.parse_with_mineru(
                    slide_id=slide_id,
                    cos_key=cos_key,
                    user_id=user_id,
                    task_id=task_id,
                    enable_formula=enable_formula,
                    enable_table=enable_table,
                    enable_style_recognition=enable_style_recognition
                )

                result = {
                    "ocr_result": ocr_result,
                }

                # 步骤2: 可选的文字去除
                if remove_text:
                    logger.info("步骤2: 开始文字去除", extra={"task_id": task_id})
                    removal_result = await service.remove_text_from_image(
                        slide_id=slide_id,
                        cos_key=cos_key,
                        user_id=user_id,
                        task_id=task_id,
                        ocr_result=ocr_result
                    )
                    result["removal_result"] = removal_result

                return result

        result = runner.run(do_recognition())

        logger.info("MinerU识别完成", extra={
            "task_id": task_id,
            "slide_id": slide_id,
            "text_count": len(result.get("ocr_result", {}).text_regions) if result.get("ocr_result") else 0,
            "edited_cos_key": result.get("removal_result", {}).get("edited_cos_key")
        })

        return {
            "task_id": task_id,
            "slide_id": slide_id,
            "cos_key": cos_key,
            "status": "completed",
            "progress": 100 if remove_text else 50,
            "text_count": len(result.get("ocr_result", {}).text_regions) if result.get("ocr_result") else 0,
            "edited_cos_key": result.get("removal_result", {}).get("edited_cos_key")
        }
