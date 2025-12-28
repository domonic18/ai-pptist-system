"""
图片编辑API端点
提供混合OCR识别和图片编辑的API接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.editing.image_editing_handler import ImageEditingHandler
from app.schemas.image_editing import (
    ParseAndRemoveRequest,
    HybridOCRParseRequest,
    MinerUParseRequest,
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Image Editing"])


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "demo_001"


@router.post(
    "/parse_with_mineru",
    response_model=StandardResponse,
    summary="MinerU识别",
    description="使用MinerU识别图片中的文字，结合多模态大模型获取样式信息"
)
async def parse_with_mineru(
    request: MinerUParseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    使用MinerU识别图片中的文字

    结合MinerU（精确坐标）和多模态大模型（样式信息）

    Args:
        request: 包含slide_id、cos_key和选项的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含task_id、status、estimated_time的任务信息
    """
    handler = ImageEditingHandler(db)
    data = await handler.handle_parse_with_mineru(request, user_id)

    return StandardResponse(
        status="success",
        message="MinerU识别任务已创建",
        data=data
    )


@router.post(
    "/parse_hybrid_ocr",
    response_model=StandardResponse,
    summary="混合OCR识别",
    description="使用混合OCR识别图片中的文字"
)
async def parse_with_hybrid_ocr(
    request: HybridOCRParseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    使用混合OCR识别图片中的文字

    结合传统OCR（精确坐标）和多模态大模型（样式信息）

    Args:
        request: 包含slide_id和cos_key的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含task_id、status、estimated_time的任务信息
    """
    handler = ImageEditingHandler(db)
    data = await handler.handle_parse_with_hybrid_ocr(request, user_id)

    return StandardResponse(
        status="success",
        message="混合OCR识别任务已创建",
        data=data
    )


@router.get(
    "/status/{task_id}",
    response_model=StandardResponse,
    summary="查询编辑状态",
    description="查询图片编辑任务的当前状态和处理结果"
)
async def get_editing_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    查询编辑状态

    返回任务的当前状态和处理结果（如果已完成）。

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务状态、进度、处理结果（如果已完成）
    """
    handler = ImageEditingHandler(db)
    data = await handler.handle_get_editing_status(task_id)

    return StandardResponse(
        status="success",
        message="查询成功",
        data=data
    )


@router.post(
    "/parse_and_remove",
    response_model=StandardResponse,
    summary="一步完成识别和去除",
    description="同时执行OCR识别和文字去除，返回完整结果"
)
async def parse_and_remove_text(
    request: ParseAndRemoveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    一步完成：OCR识别 + 文字去除

    同时执行OCR识别和文字去除，返回完整结果
    支持选择OCR引擎：mineru | hybrid_ocr

    Args:
        request: 包含slide_id、cos_key、ai_model_id和ocr_engine的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含task_id、status、estimated_time的任务信息
    """
    handler = ImageEditingHandler(db)
    data = await handler.handle_parse_and_remove_text(request, user_id)

    return StandardResponse(
        status="success",
        message="图片编辑任务已创建",
        data=data
    )
