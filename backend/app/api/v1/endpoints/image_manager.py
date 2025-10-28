"""
图片管理API端点 - 重构版本
专门处理图片的基础管理操作（列表、详情、删除、URL获取）
采用薄路由、重服务的架构设计
"""

from fastapi import APIRouter, Depends, Query, Body
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.management_handler import ManagementHandler
from app.services.image.search_handler import ImageSearchHandler
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Image Management"])


@router.get(
    "",
    response_model=StandardResponse,
    summary="获取图片列表",
    description="获取当前用户的所有图片列表，支持分页和筛选"
)
async def list_images(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    source_type: Optional[str] = Query(None, description="图片来源类型筛选：generated（AI生成）或uploaded（用户上传）"),
    tags: Optional[List[str]] = Query(None, description="标签筛选，支持多个标签"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取用户的图片列表

    Args:
        page: 页码
        limit: 每页记录数（1-100）
        source_type: 图片来源类型筛选
        tags: 标签筛选
        db: 数据库会话

    Returns:
        StandardResponse: 包含图片列表和分页信息的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理列表逻辑
    handler = ManagementHandler(db)
    skip = (page - 1) * limit

    # 根据筛选条件调用不同的处理方法
    if source_type == "generated" or (tags and "AI生成" in tags):
        # 如果筛选AI生成图片，使用专门的方法
        from app.repositories.image import ImageRepository
        repo = ImageRepository(db)

        if source_type == "generated":
            images, total = await repo.get_images_by_source_type(
                source_type="generated",
                user_id=user_id,
                skip=skip,
                limit=limit
            )
        else:
            # 使用标签筛选
            images, total = await repo.search_images_by_tags(
                tags=tags,
                user_id=user_id,
                skip=skip,
                limit=limit
            )

        # 转换为响应格式
        items = [image.to_dict() for image in images]
        list_result = {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    else:
        # 默认获取所有图片
        list_result = await handler.handle_list_images(
            user_id=user_id,
            skip=skip,
            limit=limit
        )

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message=f"成功获取 {len(list_result['items'])} 张图片",
        data=list_result
    )


@router.get(
    "/{image_id}",
    response_model=StandardResponse,
    summary="获取图片详情",
    description="获取指定图片的详细信息"
)
async def get_image_detail(
    image_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片详情

    Args:
        image_id: 图片ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含图片详细信息的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理详情获取逻辑
    handler = ManagementHandler(db)
    image_detail = await handler.handle_get_image_detail(
        image_id=image_id,
        user_id=user_id
    )

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message="成功获取图片详情",
        data=image_detail
    )


@router.get(
    "/{image_id}/url",
    response_model=StandardResponse,
    summary="获取图片访问URL",
    description="获取指定图片的访问URL（COS预签名URL或本地URL）"
)
async def get_image_access_url(
    image_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片访问URL（COS预签名URL或本地URL）

    Args:
        image_id: 图片ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含图片访问URL的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理URL获取逻辑
    handler = ManagementHandler(db)
    url_result = await handler.handle_get_image_access_url(
        image_id=image_id,
        user_id=user_id
    )

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message="成功获取图片访问URL",
        data=url_result
    )


@router.delete(
    "/{image_id}",
    response_model=StandardResponse,
    summary="删除图片",
    description="删除指定的图片，包括COS存储和数据库记录"
)
async def delete_image(
    image_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    删除图片

    Args:
        image_id: 图片ID
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理删除逻辑
    handler = ManagementHandler(db)
    await handler.handle_delete_image(
        image_id=image_id,
        user_id=user_id
    )

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message="图片删除成功",
        data={"image_id": image_id}
    )


@router.delete(
    "/batch/delete",
    response_model=StandardResponse,
    summary="批量删除图片",
    description="批量删除多张图片，支持并发处理"
)
async def batch_delete_images(
    image_ids: List[str] = Body(..., description="要删除的图片ID列表"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量删除图片

    Args:
        image_ids: 要删除的图片ID列表
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理批量删除逻辑
    handler = ManagementHandler(db)
    results = []

    for image_id in image_ids:
        try:
            success = await handler.handle_delete_image(
                image_id=image_id,
                user_id=user_id
            )
            results.append({"image_id": image_id, "success": success})
        except Exception as e:
            results.append({"image_id": image_id, "success": False, "error": str(e)})

    # 统计成功和失败的数量
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    # 返回标准化响应
    return StandardResponse(
        status="success" if successful > 0 else "partial_success",
        message=f"批量删除完成，成功: {successful}，失败: {failed}",
        data={"results": results}
    )


@router.get(
    "generation-history",
    response_model=StandardResponse,
    summary="获取图片生成历史",
    description="获取图片生成历史记录"
)
async def get_image_generation_history(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片生成历史记录

    Args:
        page: 页码，默认为1
        limit: 每页记录数，默认为20
        db: 数据库会话

    Returns:
        StandardResponse: 包含生成历史记录的响应
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理历史记录获取逻辑
    handler = ManagementHandler(db)
    history_result = await handler.handle_get_image_generation_history(
        user_id=user_id,
        page=page,
        limit=limit
    )

    # 返回标准化响应
    return StandardResponse(
        status="success",
        message="成功获取图片生成历史记录",
        data=history_result
    )