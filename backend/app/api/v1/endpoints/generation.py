"""
AI生成API端点
负责AI内容生成相关功能，如大纲生成、幻灯片生成、图片生成等
"""

from typing import AsyncGenerator, Dict, Any
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.generation_outline import OutlineGenerationRequest
from app.schemas.generation_slides import SlidesGenerationRequest
from app.schemas.image_manager import ImageGenerationAndStoreRequest, ImageGenerationAndStoreResponse
from app.schemas.common import StandardResponse
from app.services.generation.outline_stream_handler import OutlineStreamHandler
from app.services.generation.slides_stream_handler import SlidesStreamHandler
from app.services.image.image_generation_handler import ImageGenerationHandler
from app.services.image.image_generation_store_service import ImageGenerationStoreService
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["AI生成"])


@router.post(
    "/outline",
    response_class=StreamingResponse,
    summary="流式生成演示文稿大纲",
    description="根据主题和内容流式生成演示文稿大纲，使用Server-Sent Events协议"
)
async def generate_presentation_outline_stream(
    request: Request,
    generation_request: OutlineGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    流式生成演示文稿大纲 - SSE实现

    支持Server-Sent Events协议，实现渐进式大纲内容生成

    Args:
        request: FastAPI请求对象
        generation_request: 大纲生成请求参数
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应
    """

    handler = OutlineStreamHandler(db)

    async def event_generator() -> AsyncGenerator[str, None]:
        """事件生成器"""
        async for event in handler.handle_outline_stream_generation(
            generation_request,
            request
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        }
    )


@router.post(
    "/slides",
    response_class=StreamingResponse,
    summary="流式生成演示文稿幻灯片",
    description="根据大纲内容流式生成演示文稿幻灯片，使用Server-Sent Events协议"
)
async def generate_presentation_slides_stream(
    request: Request,
    generation_request: SlidesGenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    流式生成演示文稿幻灯片 - SSE实现

    支持Server-Sent Events协议，实现渐进式幻灯片内容生成

    Args:
        request: FastAPI请求对象
        generation_request: 幻灯片生成请求参数
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应
    """

    handler = SlidesStreamHandler(db)

    async def event_generator() -> AsyncGenerator[str, None]:
        """事件生成器"""
        async for event in handler.handle_slides_stream_generation(
            generation_request,
            request
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        }
    )


# 图片生成相关路由
@router.post(
    "/image",
    response_model=StandardResponse,
    summary="生成图片",
    description="根据文本描述生成图片"
)
async def generate_image(
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    生成图片接口

    Args:
        request_data: 生成请求参数，包含prompt、model_name、width、height、quality、style等
        db: 数据库会话

    Returns:
        StandardResponse: 生成结果
    """
    try:
        handler = ImageGenerationHandler(db)
        result = await handler.handle_generate_image(request_data)

        if result.get("success"):
            return StandardResponse(
                status="success",
                message=result.get("message", "图片生成成功"),
                data=result
            )
        else:
            return StandardResponse(
                status="error",
                message=result.get("message", "图片生成失败"),
                data=result
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("生成图片失败", extra={'error': str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成图片失败: {str(e)}"
        ) from e


@router.post(
    "/image/store",
    response_model=StandardResponse,
    summary="生成图片并存储",
    description="根据文本描述生成图片并存储到COS和数据库"
)
async def generate_and_store_image(
    request: ImageGenerationAndStoreRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    生成图片并存储接口

    功能流程：
    1. 调用AI模型生成图片
    2. 下载生成的图片内容
    3. 上传到COS存储
    4. 创建数据库记录并标记为AI生成

    Args:
        request: 图片生成和存储请求参数
        db: 数据库会话

    Returns:
        StandardResponse[ImageGenerationAndStoreResponse]: 生成和存储结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用AI生成图片存储服务
        store_service = ImageGenerationStoreService(db)
        result = await store_service.generate_and_store_image(request, user_id)

        if result["success"]:
            return StandardResponse(
                status="success",
                message=result["message"],
                data={
                    "success": True,
                    "image_id": result["image_id"],
                    "image_url": result["image_url"],
                    "cos_key": result["cos_key"]
                }
            )
        else:
            return StandardResponse(
                status="error",
                message=result["message"],
                data={
                    "success": False,
                    "error": result.get("error")
                }
            )

    except Exception as e:
        logger.error(f"生成图片并存储接口异常: {e}")
        return StandardResponse(
            status="error",
            message="生成图片并存储失败",
            data={
                "success": False,
                "error": str(e)
            }
        )



