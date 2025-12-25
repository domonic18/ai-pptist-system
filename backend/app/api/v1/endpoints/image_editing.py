"""
图片编辑API端点
提供混合OCR识别和图片编辑的API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime

from app.repositories.image_editing import ImageEditingRepository
from app.services.editing.image_editing_service import ImageEditingService
from app.db.database import get_db
from app.schemas.image_editing import (
    ParseAndRemoveRequest,
    HybridOCRParseRequest,
    RemoveTextRequest,
    EditingTaskResponse,
    EditingStatusResponse,
    EditingResultResponse,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "demo_001"


router = APIRouter(tags=["image_editing"])


@router.post("/parse_hybrid_ocr", response_model=Dict[str, Any])
async def parse_with_hybrid_ocr(
    request: HybridOCRParseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    使用混合OCR识别图片中的文字

    结合传统OCR（精确坐标）和多模态大模型（样式信息）

    Args:
        request: 包含slide_id和cos_key的请求
        user_id: 当前用户ID

    Returns:
        Dict: 包含task_id、status、estimated_time的任务信息
    """
    try:
        logger.info(
            "收到混合OCR识别请求",
            extra={
                "slide_id": request.slide_id,
                "cos_key": request.cos_key
            }
        )

        repo = ImageEditingRepository(db)

        # 生成任务ID
        task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 创建任务记录
        await repo.create_task(
            task_id=task_id,
            slide_id=request.slide_id,
            original_cos_key=request.cos_key,
            user_id=user_id
        )

        # 提交到Celery队列
        from app.services.tasks.image_editing_tasks import hybrid_ocr_task
        celery_task = hybrid_ocr_task.apply_async(
            kwargs={
                "task_id": task_id,
                "slide_id": request.slide_id,
                "cos_key": request.cos_key,
                "user_id": user_id
            },
            queue="image_editing"
        )

        logger.info(
            "混合OCR任务已提交到Celery队列",
            extra={
                "task_id": task_id,
                "celery_task_id": celery_task.id,
                "slide_id": request.slide_id
            }
        )

        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 8,
                "message": "OCR识别任务已创建，正在处理中"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(
            "混合OCR任务创建失败",
            extra={
                "slide_id": request.slide_id,
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "TASK_CREATE_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_editing_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    查询编辑状态

    返回任务的当前状态和处理结果（如果已完成）。

    Args:
        task_id: 任务ID

    Returns:
        Dict: 包含任务状态、进度、处理结果（如果已完成）
    """
    try:
        from app.services.editing.image_editing_service import ImageEditingService

        service = ImageEditingService(db)
        result = await service.get_editing_result(task_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "data": None,
                    "error": {"message": "任务不存在", "code": "TASK_NOT_FOUND"},
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": str(uuid.uuid4())
                }
            )

        logger.debug(
            "查询编辑状态",
            extra={
                "task_id": task_id,
                "status": result["status"],
                "progress": result["progress"]
            }
        )

        # 构建响应数据
        response_data = {
            "task_id": result["task_id"],
            "slide_id": result["slide_id"],
            "status": result["status"],
            "progress": result["progress"]
        }

        # 添加当前步骤
        if result.get("current_step"):
            response_data["current_step"] = result["current_step"]

        # 如果已完成，包含完整结果
        if result["status"] == "completed":
            if result.get("ocr_result"):
                response_data["ocr_result"] = result["ocr_result"]
            if result.get("edited_image"):
                response_data["edited_image"] = result["edited_image"]

        # 如果失败，包含错误信息
        if result.get("error_message"):
            response_data["error_message"] = result["error_message"]

        return {
            "success": True,
            "data": response_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "查询编辑状态失败",
            extra={"task_id": task_id, "error": str(e)}
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "STATUS_QUERY_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.post("/parse_and_remove", response_model=Dict[str, Any])
async def parse_and_remove_text(
    request: ParseAndRemoveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    一步完成：OCR识别 + 文字去除

    同时执行混合OCR识别和文字去除，返回完整结果

    Args:
        request: 包含slide_id和cos_key的请求
        user_id: 当前用户ID

    Returns:
        Dict: 包含task_id、status、estimated_time的任务信息
    """
    try:
        logger.info(
            "收到图片编辑请求（一步完成）",
            extra={
                "slide_id": request.slide_id,
                "cos_key": request.cos_key
            }
        )

        repo = ImageEditingRepository(db)

        # 生成任务ID
        task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 创建任务记录
        await repo.create_task(
            task_id=task_id,
            slide_id=request.slide_id,
            original_cos_key=request.cos_key,
            user_id=user_id
        )

        # 提交到Celery队列（完整编辑任务）
        from app.services.tasks.image_editing_tasks import full_editing_task
        celery_task = full_editing_task.apply_async(
            kwargs={
                "task_id": task_id,
                "slide_id": request.slide_id,
                "cos_key": request.cos_key,
                "user_id": user_id
            },
            queue="image_editing"
        )

        logger.info(
            "图片编辑任务已提交到Celery队列",
            extra={
                "task_id": task_id,
                "celery_task_id": celery_task.id,
                "slide_id": request.slide_id
            }
        )

        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 20,
                "message": "编辑任务已创建，正在处理中"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(
            "图片编辑任务创建失败",
            extra={
                "slide_id": request.slide_id,
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "TASK_CREATE_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )
