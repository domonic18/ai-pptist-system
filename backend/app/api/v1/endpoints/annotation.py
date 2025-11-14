"""
标注API端点

遵循项目API设计规范:
- 轻路由：只处理HTTP请求和响应
- 参数验证和序列化
- 调用Handler处理业务逻辑
- 返回StandardResponse
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from app.db.database import get_db
from app.services.annotation.annotation_handler import AnnotationHandler
from app.schemas.annotation import (
    AnnotationStartRequest,
    AnnotationProgressResponse,
    AnnotationResultResponse
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

logger = get_logger(__name__)

router = APIRouter(tags=["Annotation"])


@router.post(
    "/start",
    response_model=StandardResponse,
    summary="启动自动标注",
    description="启动PPT模板的自动标注任务"
)
async def start_annotation(
    request: AnnotationStartRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    启动自动标注任务

    Args:
        request: 标注请求参数
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务ID的响应
    """
    try:
        logger.info(
            log_messages.START_OPERATION,
            operation_name="自动标注",
            extra={
                "slide_count": len(request.slides),
                "model_id": request.model_config.model_id if request.model_config else None
            }
        )

        # TODO: 从认证中获取用户ID（暂时使用固定值）
        user_id = "demo_001"

        handler = AnnotationHandler(db)
        result = await handler.handle_start_annotation(request, user_id)

        logger.info(
            log_messages.OPERATION_SUCCESS,
            operation_name="启动自动标注",
            extra={"task_id": result["task_id"]}
        )

        return StandardResponse(
            status="success",
            message="自动标注任务已启动",
            data=result
        )

    except Exception as e:
        logger.error(
            log_messages.OPERATION_FAILED,
            operation_name="启动自动标注",
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动标注任务失败: {str(e)}"
        )


@router.get(
    "/progress/{task_id}",
    response_model=StandardResponse,
    summary="获取标注进度",
    description="查询标注任务的当前进度"
)
async def get_annotation_progress(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取标注进度

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含进度信息的响应
    """
    try:
        handler = AnnotationHandler(db)
        result = await handler.handle_get_progress(task_id)

        return StandardResponse(
            status="success",
            message="标注进度查询成功",
            data=result
        )

    except Exception as e:
        logger.error(
            log_messages.OPERATION_FAILED,
            operation_name="查询标注进度",
            extra={"task_id": task_id},
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询进度失败: {str(e)}"
        )


@router.get(
    "/results/{task_id}",
    response_model=StandardResponse,
    summary="获取标注结果",
    description="获取标注任务的完整结果"
)
async def get_annotation_results(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取标注结果

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含标注结果的响应
    """
    try:
        handler = AnnotationHandler(db)
        result = await handler.handle_get_results(task_id)

        return StandardResponse(
            status="success",
            message="标注结果获取成功",
            data=result
        )

    except Exception as e:
        logger.error(
            log_messages.OPERATION_FAILED,
            operation_name="获取标注结果",
            extra={"task_id": task_id},
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取结果失败: {str(e)}"
        )


@router.post(
    "/corrections",
    response_model=StandardResponse,
    summary="提交用户修正",
    description="提交用户对标注结果的修正"
)
async def submit_corrections(
    task_id: str = Body(..., description="任务ID"),
    corrections: List[Dict[str, Any]] = Body(..., description="修正数据列表"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    提交用户修正

    Args:
        task_id: 任务ID
        corrections: 修正数据
        db: 数据库会话

    Returns:
        StandardResponse: 修正结果响应
    """
    try:
        handler = AnnotationHandler(db)
        result = await handler.handle_submit_corrections(task_id, corrections)

        return StandardResponse(
            status="success",
            message="用户修正已应用",
            data=result
        )

    except Exception as e:
        logger.error(
            log_messages.OPERATION_FAILED,
            operation_name="提交用户修正",
            extra={"task_id": task_id},
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交修正失败: {str(e)}"
        )