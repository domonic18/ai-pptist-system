"""
标签管理API端点
处理标签的增删改查操作
"""

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.tag_handler import TagHandler
from app.schemas.tag import TagCreate, TagSearchParams, TagListResponse, PopularTagResponse
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Tags"])


@router.get(
    "",
    response_model=StandardResponse,
    summary="获取标签列表",
    description="获取所有标签，支持搜索和分页"
)
async def get_all_tags(
    query: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    sort_by: str = Query("usage_count", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取标签列表

    Args:
        query: 搜索关键词
        page: 页码
        limit: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向
        db: 数据库会话

    Returns:
        StandardResponse: 包含标签列表的响应
    """
    try:
        # 构建搜索参数
        search_params = TagSearchParams(
            query=query,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 使用业务处理器处理标签列表逻辑
        handler = TagHandler(db)
        tags_result = await handler.handle_get_all_tags(search_params)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"成功获取 {len(tags_result['items'])} 个标签",
            data=tags_result
        )

    except Exception as e:
        logger.error(f"获取标签列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取标签列表失败")


@router.get(
    "/popular",
    response_model=StandardResponse,
    summary="获取热门标签",
    description="获取使用次数最多的热门标签"
)
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="标签数量限制"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取热门标签

    Args:
        limit: 标签数量限制
        db: 数据库会话

    Returns:
        StandardResponse: 包含热门标签的响应
    """
    try:
        # 使用业务处理器处理热门标签逻辑
        handler = TagHandler(db)
        popular_result = await handler.handle_get_popular_tags(limit)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"成功获取 {len(popular_result['tags'])} 个热门标签",
            data=popular_result
        )

    except Exception as e:
        logger.error(f"获取热门标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取热门标签失败")


@router.post(
    "",
    response_model=StandardResponse,
    summary="创建标签",
    description="创建新的标签"
)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    创建标签

    Args:
        tag_data: 标签数据
        db: 数据库会话

    Returns:
        StandardResponse: 创建结果
    """
    try:
        # 使用业务处理器处理标签创建逻辑
        handler = TagHandler(db)
        create_result = await handler.handle_create_tag(tag_data)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=create_result["message"],
            data=create_result
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建标签失败")


@router.delete(
    "/{tag_name}",
    response_model=StandardResponse,
    summary="删除标签",
    description="删除指定名称的标签"
)
async def delete_tag(
    tag_name: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    删除标签

    Args:
        tag_name: 标签名称
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果
    """
    try:
        # 使用业务处理器处理标签删除逻辑
        handler = TagHandler(db)
        delete_result = await handler.handle_delete_tag(tag_name)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=delete_result["message"],
            data=delete_result
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除标签失败")


@router.get(
    "/search",
    response_model=StandardResponse,
    summary="搜索标签",
    description="根据关键词搜索标签"
)
async def search_tags(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="标签数量限制"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    搜索标签

    Args:
        query: 搜索关键词
        limit: 标签数量限制
        db: 数据库会话

    Returns:
        StandardResponse: 搜索结果
    """
    try:
        # 使用业务处理器处理标签搜索逻辑
        handler = TagHandler(db)
        search_result = await handler.handle_search_tags(query, limit)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"搜索到 {len(search_result['tags'])} 个相关标签",
            data=search_result
        )

    except Exception as e:
        logger.error(f"搜索标签失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索标签失败")