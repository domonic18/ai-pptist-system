"""
标注API端点

遵循项目API设计规范:
- 轻路由：只处理HTTP请求和响应
- 参数验证和序列化
- 调用Handler处理业务逻辑
- 返回StandardResponse
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.annotation.annotation_handler import AnnotationHandler
from app.schemas.annotation import (
    SingleAnnotationRequest,
    BatchAnnotationRequest
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["自动标注"])


@router.post(
    "/single",
    response_model=StandardResponse,
    summary="单张幻灯片同步标注",
    description="单张幻灯片同步标注，直接返回标注结果"
)
async def annotate_single_slide(
    request: SingleAnnotationRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    单张幻灯片同步标注

    **功能说明**：
    - 单张幻灯片标注
    - 同步返回结果（无需轮询）
    - 适用于快速标注场景

    Args:
        request: 单张幻灯片标注请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含标注结果的响应
    """
    # 验证请求
    logger.info(
        "收到单张幻灯片标注请求",
        extra={"slide_id": request.slide.get("slide_id")}
    )

    handler = AnnotationHandler(db)
    result = await handler.handle_annotate_single_slide(request)

    logger.info(
        "单张幻灯片标注成功",
        extra={"slide_id": request.slide.get("slide_id")}
    )

    return StandardResponse(
        status="success",
        message="标注完成",
        data=result
    )


@router.post(
    "/batch",
    response_model=StandardResponse,
    summary="批量幻灯片异步标注",
    description="多张幻灯片批量标注，异步处理，返回task_id"
)
async def batch_annotate_slides(
    request: BatchAnnotationRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量幻灯片异步标注

    **功能说明**：
    - 多张幻灯片批量标注
    - 异步处理，返回task_id
    - 适用于批量标注场景

    Args:
        request: 批量标注请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务ID的响应
    """
    # 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    logger.info(
        "收到批量标注请求",
        extra={
            "user_id": user_id,
            "slide_count": len(request.slides)
        }
    )

    handler = AnnotationHandler(db)
    result = await handler.handle_batch_annotation_start(request, user_id)

    return StandardResponse(
        status="success",
        message="批量标注任务已启动",
        data=result
    )
