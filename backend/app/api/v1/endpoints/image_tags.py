"""
图片标签管理API端点
处理图片标签的增删改查操作
"""

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.tag_handler import TagHandler
from app.schemas.tag import (
    ImageTagUpdate, ImageTagAdd, TagCreate, TagSearchParams,
    TagListResponse, PopularTagResponse,
    BatchImageTagOperation, BatchImageTagResponse
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Image Tags"])


@router.get(
    "/{image_id}/tags",
    response_model=StandardResponse,
    summary="获取图片标签",
    description="获取指定图片的所有标签"
)
async def get_image_tags(
    image_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片标签

    Args:
        image_id: 图片ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含图片标签的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理标签获取逻辑
        handler = TagHandler(db)
        tags_result = await handler.handle_get_image_tags(
            image_id=image_id,
            user_id=user_id
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message="成功获取图片标签",
            data=tags_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取图片标签失败")


@router.post(
    "/{image_id}/tags",
    response_model=StandardResponse,
    summary="添加图片标签",
    description="为指定图片添加标签"
)
async def add_image_tags(
    image_id: str,
    tag_data: ImageTagAdd,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    添加图片标签

    Args:
        image_id: 图片ID
        tag_data: 标签数据
        db: 数据库会话

    Returns:
        StandardResponse: 添加结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理标签添加逻辑
        handler = TagHandler(db)
        add_result = await handler.handle_add_image_tags(
            image_id=image_id,
            user_id=user_id,
            tag_data=tag_data
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message="成功添加图片标签",
            data=add_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"添加图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加图片标签失败")


@router.put(
    "/{image_id}/tags",
    response_model=StandardResponse,
    summary="更新图片标签",
    description="更新指定图片的所有标签"
)
async def update_image_tags(
    image_id: str,
    tag_data: ImageTagUpdate,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    更新图片标签

    Args:
        image_id: 图片ID
        tag_data: 标签数据
        db: 数据库会话

    Returns:
        StandardResponse: 更新结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理标签更新逻辑
        handler = TagHandler(db)
        update_result = await handler.handle_update_image_tags(
            image_id=image_id,
            user_id=user_id,
            tag_data=tag_data
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message="成功更新图片标签",
            data=update_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新图片标签失败")


@router.delete(
    "/{image_id}/tags",
    response_model=StandardResponse,
    summary="删除图片标签",
    description="删除指定图片的所有标签或指定标签"
)
async def delete_image_tags(
    image_id: str,
    tags: Optional[List[str]] = Body(None, description="要删除的标签列表，为空则删除所有标签"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    删除图片标签

    Args:
        image_id: 图片ID
        tags: 要删除的标签列表
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理标签删除逻辑
        handler = TagHandler(db)
        delete_result = await handler.handle_delete_image_tags(
            image_id=image_id,
            user_id=user_id,
            tags_to_delete=tags
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message="成功删除图片标签",
            data=delete_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除图片标签失败")


@router.delete(
    "/{image_id}/tags/{tag}",
    response_model=StandardResponse,
    summary="删除特定图片标签",
    description="删除指定图片的特定标签"
)
async def delete_specific_image_tag(
    image_id: str,
    tag: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    删除特定图片标签

    Args:
        image_id: 图片ID
        tag: 要删除的标签
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理标签删除逻辑
        handler = TagHandler(db)
        delete_result = await handler.handle_delete_image_tags(
            image_id=image_id,
            user_id=user_id,
            tags_to_delete=[tag]
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"成功删除标签 '{tag}'",
            data=delete_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除图片标签失败")


@router.post(
    "/search/by-tags",
    response_model=StandardResponse,
    summary="根据标签搜索图片",
    description="根据标签列表搜索图片"
)
async def search_images_by_tags(
    tags: List[str] = Body(..., description="搜索标签列表"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    根据标签搜索图片

    Args:
        tags: 搜索标签列表
        page: 页码
        limit: 每页记录数
        db: 数据库会话

    Returns:
        StandardResponse: 搜索结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        skip = (page - 1) * limit

        # 使用业务处理器处理标签搜索逻辑
        handler = TagHandler(db)
        search_result = await handler.handle_search_images_by_tags(
            user_id=user_id,
            tags=tags,
            skip=skip,
            limit=limit
        )

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"根据标签搜索到 {len(search_result['items'])} 张图片",
            data=search_result
        )

    except Exception as e:
        logger.error(f"根据标签搜索图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索图片失败")


@router.post(
    "/batch-tags",
    response_model=StandardResponse,
    summary="批量操作图片标签",
    description="批量为多个图片添加、删除或替换标签"
)
async def batch_operate_image_tags(
    batch_data: BatchImageTagOperation,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量操作图片标签

    Args:
        batch_data: 批量操作数据
        db: 数据库会话

    Returns:
        StandardResponse: 包含操作结果的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    try:
        # 使用业务处理器处理批量标签操作
        handler = TagHandler(db)
        batch_result = await handler.handle_batch_operate_image_tags(batch_data, user_id)

        # 构建操作结果消息
        if batch_result["failed_count"] == 0:
            message = f"成功为 {batch_result['success_count']} 张图片{operation_map[batch_data.operation]}标签"
        else:
            message = f"完成操作：成功 {batch_result['success_count']} 张，失败 {batch_result['failed_count']} 张"

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=message,
            data=batch_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量操作图片标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量操作图片标签失败")


# 操作类型映射字典
operation_map = {
    "add": "添加",
    "remove": "删除",
    "replace": "替换"
}