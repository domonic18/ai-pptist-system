"""
图片搜索API端点
专门处理图片搜索相关的操作
采用薄路由、重服务的架构设计
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.search.handler import ImageSearchHandler
from app.schemas.image_search import (
    ImageSearchRequest,
    TagSearchRequest,
    SearchStatistics
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["图片搜索"])


@router.post(
    "",
    response_model=StandardResponse,
    summary="搜索图片",
    description="根据提示词搜索相关图片"
)
async def search_images(
    request: ImageSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    搜索图片

    Args:
        request: 图片搜索请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含搜索结果的标准化响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理搜索逻辑
    handler = ImageSearchHandler(db)
    search_result = await handler.handle_search_images(
        query=request.prompt,
        user_id=user_id,
        limit=request.limit,
        match_threshold=request.match_threshold
    )

    # 返回标准化响应格式
    return StandardResponse(
        status="success",
        message=f"成功搜索到 {search_result['total']} 张图片",
        data={
            "results": search_result["results"],
            "total": search_result["total"],
            "query": request.prompt,
            "match_threshold": request.match_threshold,
            "limit": request.limit
        }
    )


@router.post(
    "/tags",
    response_model=StandardResponse,
    summary="按标签搜索图片",
    description="根据标签列表搜索相关图片"
)
async def search_images_by_tags(
    request: TagSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    按标签搜索图片

    Args:
        request: 标签搜索请求
        db: 数据库会话

    Returns:
        StandardResponse: 包含搜索结果的标准化响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理标签搜索逻辑
    handler = ImageSearchHandler(db)
    search_result = await handler.handle_search_by_tags(
        tags=request.tags,
        user_id=user_id,
        limit=request.limit
    )

    # 返回标准化响应格式
    return StandardResponse(
        status="success",
        message=f"通过标签搜索到 {search_result['total']} 张图片",
        data={
            "results": search_result["results"],
            "total": search_result["total"],
            "tags": request.tags,
            "limit": request.limit
        }
    )


@router.get(
    "/tags",
    response_model=StandardResponse,
    summary="获取用户标签",
    description="获取当前用户的所有图片标签"
)
async def get_user_tags(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取用户标签

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 包含标签列表的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理标签获取逻辑
    handler = ImageSearchHandler(db)
    tags = await handler.handle_get_user_tags(user_id)

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message=f"成功获取 {len(tags)} 个标签",
        data={"tags": tags}
    )


@router.get(
    "/statistics",
    response_model=StandardResponse,
    summary="获取搜索统计信息",
    description="返回用户的图片搜索统计信息"
)
async def get_search_statistics(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取搜索统计信息

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 包含统计信息的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理统计信息获取逻辑
    handler = ImageSearchHandler(db)
    statistics = await handler.handle_get_search_statistics(user_id)

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message="成功获取搜索统计信息",
        data=statistics
    )