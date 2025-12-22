"""
Banana生成PPT API端点
提供批量生成PPT幻灯片图片的功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.services.generation.banana_generation_service import BananaGenerationService
from app.services.generation.banana_task_manager import BananaTaskManager
from app.core.cache.redis import get_redis
from app.db.database import get_db
from app.repositories.banana_generation import BananaGenerationRepository
from app.core.log_utils import get_logger
from app.core.config import settings
from app.models.banana_generation_task import TaskStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/banana_generation", tags=["banana"])


# 请求和响应模型（已在frontend中定义，这里添加，因为架构设计说明需要）

class OutlineData(BaseModel):
    """PPT大纲数据"""
    title: str = Field(..., description="PPT主标题")
    slides: list[dict] = Field(..., description="幻灯片列表，每个包含title和points")


class CanvasSize(BaseModel):
    """画布尺寸"""
    width: int = Field(default=1920, description="画布宽度")
    height: int = Field(default=1080, description="画布高度")


class GenerateBatchSlidesRequest(BaseModel):
    """批量生成PPT请求"""
    outline: OutlineData = Field(..., description="PPT大纲数据")
    template_id: str = Field(..., description="模板ID")
    generation_model: str = Field(default="gemini-3-pro-image-preview", description="生成模型名称")
    canvas_size: CanvasSize = Field(default_factory=CanvasSize, description="画布尺寸")


class GenerateBatchSlidesResponse(BaseModel):
    """批量生成响应"""
    task_id: str = Field(..., description="生成任务ID")
    celery_task_id: str = Field(..., description="Celery任务ID")
    total_slides: int = Field(..., description="总幻灯片数")
    status: str = Field(default="processing", description="任务状态")


class SlideGenerationResult(BaseModel):
    """单页生成结果"""
    index: int = Field(..., description="幻灯片索引")
    title: Optional[str] = Field(None, description="标题")
    status: str = Field(..., description="状态: pending|processing|completed|failed")
    image_url: Optional[str] = Field(None, description="COS图片URL")
    generation_time: Optional[float] = Field(None, description="生成耗时(秒)")
    error: Optional[str] = Field(None, description="错误信息")


class GenerationStatusResponse(BaseModel):
    """生成状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: dict = Field(..., description="进度信息: {total, completed, failed, pending}")
    slides: list[SlideGenerationResult] = Field(..., description="每页状态列表")


class TemplateResponse(BaseModel):
    """模板列表响应"""
    templates: list[dict] = Field(..., description="模板列表")


class StopGenerationResponse(BaseModel):
    """停止生成响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    completed_slides: int = Field(..., description="已完成的幻灯片数")
    total_slides: int = Field(..., description="总幻灯片数")


# API端点实现

@router.post("/generate_batch_slides", response_model=Dict[str, Any])
async def generate_batch_slides(
    request: GenerateBatchSlidesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    批量生成PPT幻灯片图片

    流程：
    1. 接收PPT大纲和模板信息
    2. 创建生成任务记录
    3. 提交Celery任务到队列
    4. 立即返回task_id，前端轮询获取结果

    Args:
        request: 包含大纲、模板ID、生成模型等信息的请求
        user_id: 当前用户ID

    Returns:
        Dict: 包含task_id、total_slides、status的任务信息
    """
    try:
        logger.info("收到批量生成PPT请求", extra={
            "template_id": request.template_id,
            "total_slides": len(request.outline.slides),
            "generation_model": request.generation_model
        })

        service = BananaGenerationService()

        result = await service.generate_batch_slides(
            outline=request.outline.dict(),
            template_id=request.template_id,
            generation_model=request.generation_model,
            canvas_size=request.canvas_size.dict(),
            user_id=user_id
        )

        return {
            "success": True,
            "data": result,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error("批量生成PPT失败", extra={
            "error": str(e),
            "template_id": request.template_id
        })

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "GENERATION_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.get("/generation_status/{task_id}", response_model=Dict[str, Any])
async def get_generation_status(task_id: str):
    """
    查询生成任务状态（前端轮询端点）

    核心机制：前端每2秒查询一次，获取最新进度和已完成的图片URL
    Redis状态由Celery Worker在生成完成后更新

    Args:
        task_id: 生成任务ID

    Returns:
        Dict: 包含任务状态、进度、每页详细状态（含COS图片URL）
    """
    try:
        service = BananaGenerationService()

        status_data = await service.get_generation_status(task_id)

        logger.debug("查询生成状态", extra={
            "task_id": task_id,
            "status": status_data.get("status"),
            "completed": status_data.get("progress", {}).get("completed", 0),
            "total": status_data.get("progress", {}).get("total", 0)
        })

        return {
            "success": True,
            "data": status_data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error("查询生成状态失败", extra={
            "task_id": task_id,
            "error": str(e)
        })

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


@router.post("/stop_generation/{task_id}", response_model=Dict[str, Any])
async def stop_generation(task_id: str):
    """
    停止生成任务

    取消正在进行的Celery任务，并更新任务状态

    Args:
        task_id: 任务ID

    Returns:
        Dict: 停止结果
    """
    try:
        service = BananaGenerationService()

        result = await service.stop_generation(task_id)

        logger.info("停止生成任务", extra={
            "task_id": task_id,
            "completed_slides": result.get("completed_slides")
        })

        return {
            "success": True,
            "data": result,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error("停止生成失败", extra={
            "task_id": task_id,
            "error": str(e)
        })

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "STOP_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.post("/regenerate_slide", response_model=Dict[str, Any])
async def regenerate_slide(
    request: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    重新生成单张幻灯片

    用于替换生成失败的页面或重新生成不满意的结果

    Args:
        request: 包含task_id和slide_index的请求
        user_id: 当前用户ID

    Returns:
        Dict: 包含slide_index、status、celery_task_id的结果
    """
    try:
        task_id = request.get("task_id")
        slide_index = request.get("slide_index")

        if not task_id or slide_index is None:
            raise ValueError("task_id和slide_index是必填参数")

        service = BananaGenerationService()

        result = await service.regenerate_slide(task_id, slide_index)

        logger.info("重新生成幻灯片", extra={
            "task_id": task_id,
            "slide_index": slide_index
        })

        return {
            "success": True,
            "data": result,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error("重新生成失败", extra={
            "task_id": request.get("task_id"),
            "slide_index": request.get("slide_index"),
            "error": str(e)
        })

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "REGENERATE_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


@router.get("/templates", response_model=Dict[str, Any])
async def get_templates(
    type: str = Query(None, description="模板类型: system|user"),
    aspect_ratio: str = Query(None, description="宽高比: 16:9|4:3")
):
    """
    获取可用模板列表

    返回系统中可用的PPT模板，包括系统预设和用户上传的

    Args:
        type: 模板类型过滤（可选）
        aspect_ratio: 宽高比过滤（可选）

    Returns:
        Dict: 包含templates数组
    """
    try:
        service = BananaGenerationService()

        result = service.get_templates(type=type, aspect_ratio=aspect_ratio)

        logger.info("获取模板列表", extra={
            "template_count": len(result.get("templates", [])),
            "type": type,
            "aspect_ratio": aspect_ratio
        })

        return {
            "success": True,
            "data": result,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error("获取模板列表失败", extra={
            "error": str(e),
            "type": type,
            "aspect_ratio": aspect_ratio
        })

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "data": None,
                "error": {"message": str(e), "code": "GET_TEMPLATES_FAILED"},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "user_test_001"
