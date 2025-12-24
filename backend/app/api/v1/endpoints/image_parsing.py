"""
图片解析API端点
提供图片文字识别的API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime

from app.services.parsing.image_parsing_service import ImageParsingService
from app.db.database import get_db
from app.schemas.image_parsing import (
    ParseRequest, ParseTaskResponse, ParseStatusResponse
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "demo_001"


router = APIRouter(tags=["image_parsing"])


@router.post("/parse", response_model=Dict[str, Any])
async def parse_image(
    request: ParseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    解析图片中的文字

    提交图片解析任务，返回任务ID。前端需要轮询查询任务状态获取解析结果。

    Args:
        request: 包含slide_id和cos_key的请求
        user_id: 当前用户ID

    Returns:
        Dict: 包含task_id、status、estimated_time的任务信息
    """
    try:
        logger.info(
            "收到图片解析请求",
            extra={
                "slide_id": request.slide_id,
                "cos_key": request.cos_key
            }
        )

        service = ImageParsingService(db)

        # 执行解析（同步等待结果，MVP阶段简化）
        result = await service.parse_image(
            slide_id=request.slide_id,
            cos_key=request.cos_key,
            user_id=user_id
        )

        return {
            "success": True,
            "data": {
                "task_id": result.task_id,
                "status": result.status,
                "estimated_time": 5,
                "message": "解析完成" if result.status == "completed" else "处理中"
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(
            "图片解析失败",
            extra={
                "slide_id": request.slide_id,
                "cos_key": request.cos_key,
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "PARSE_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_parse_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    查询解析状态

    返回任务的当前状态和解析结果（如果已完成）。

    Args:
        task_id: 任务ID

    Returns:
        Dict: 包含任务状态、进度、解析结果（如果已完成）
    """
    try:
        service = ImageParsingService(db)

        result = await service.get_parse_result(task_id)

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
            "查询解析状态",
            extra={
                "task_id": task_id,
                "status": result.status,
                "progress": result.progress
            }
        )

        # 构建响应数据
        response_data = {
            "task_id": result.task_id,
            "slide_id": result.slide_id,
            "cos_key": result.cos_key,
            "status": result.status,
            "progress": result.progress
        }

        # 如果已完成，包含完整结果
        if result.status == "completed":
            response_data["text_regions"] = [
                region.dict() for region in result.text_regions
            ]
            response_data["metadata"] = result.metadata.dict()

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
            "查询解析状态失败",
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
