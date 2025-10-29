"""
布局优化API端点（轻路由）
负责参数验证、调用Handler、返回标准响应
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.layout_optimization import (
    LayoutOptimizationRequest,
    LayoutOptimizationResponseData
)
from app.schemas.common import StandardResponse
from app.services.layout.layout_optimization_handler import LayoutOptimizationHandler
from app.core.log_utils import get_logger

logger = get_logger(__name__)

# 注意：使用空字符串""作为根路径，prefix在router.py中统一管理
router = APIRouter(tags=["布局优化"])


@router.post(
    "/optimize",  # 完整路径：/api/v1/layout/optimize
    response_model=StandardResponse,
    summary="优化幻灯片布局",
    description="使用LLM智能优化幻灯片的排版布局，保持内容不变"
)
async def optimize_slide_layout(
    request: LayoutOptimizationRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    优化幻灯片布局的API端点

    Args:
        request: 布局优化请求（Pydantic自动验证）
        db: 数据库会话

    Returns:
        StandardResponse: 标准响应格式
            - status: "success" | "error" | "warning"
            - message: 响应消息
            - data: LayoutOptimizationResponseData | None
            - error_code: 错误码（可选）
            - error_details: 错误详情（可选）
    """
    try:
        # 调用Handler处理业务
        handler = LayoutOptimizationHandler(db)
        result = await handler.handle_optimize_layout(request)

        # 返回标准响应
        return StandardResponse(
            status="success",
            message="布局优化完成",
            data=result
        )

    except HTTPException:
        # FastAPI会自动处理HTTPException
        raise

    except Exception as e:
        # 捕获未预期的异常
        logger.error(
            "布局优化端点异常",
            operation="optimize_slide_layout_endpoint",
            slide_id=request.slide_id if request else None,
            error=str(e),
            error_type=type(e).__name__
        )

        return StandardResponse(
            status="error",
            message="布局优化失败",
            error_code="LAYOUT_OPTIMIZATION_ERROR",
            error_details={"error": str(e)}
        )