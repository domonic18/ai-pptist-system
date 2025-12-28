"""
图片解析API端点
提供图片文字识别的API接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.parsing.image_parsing.handler import ImageParsingHandler
from app.schemas.image_parsing import ParseRequest
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["图片解析"])


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "demo_001"


@router.post(
    "/parse",
    response_model=StandardResponse,
    summary="解析图片",
    description="提交图片解析任务到Celery队列，返回任务ID"
)
async def parse_image(
    request: ParseRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    解析图片中的文字

    提交图片解析任务到Celery队列，返回任务ID。
    前端需要轮询查询任务状态获取解析结果。

    Args:
        request: 包含slide_id和cos_key的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含task_id、status、estimated_time的任务信息
    """
    handler = ImageParsingHandler(db)
    data = await handler.handle_parse_image(request, user_id)

    return StandardResponse(
        status="success",
        message="图片解析任务已创建",
        data=data
    )


@router.get(
    "/status/{task_id}",
    response_model=StandardResponse,
    summary="查询解析状态",
    description="查询图片解析任务的当前状态和解析结果"
)
async def get_parse_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    查询解析状态

    返回任务的当前状态和解析结果（如果已完成）。

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务状态、进度、解析结果（如果已完成）
    """
    handler = ImageParsingHandler(db)
    data = await handler.handle_get_parse_status(task_id)

    return StandardResponse(
        status="success",
        message="查询成功",
        data=data
    )
