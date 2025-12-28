"""
标签库管理业务处理器
处理标签库管理的网络请求、日志记录和异常处理
"""

from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tag.library.service import TagLibraryService
from app.schemas.tag_library import TagCreate, TagSearchParams
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class TagLibraryHandler:
    """标签库处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_library_service = TagLibraryService(db)

    async def handle_get_all_tags(
        self,
        search_params: TagSearchParams
    ) -> Dict[str, Any]:
        """处理获取所有标签请求"""
        try:
            logger.info(
                "处理获取所有标签请求",
                extra={
                    "query": search_params.query,
                    "page": search_params.page,
                    "limit": search_params.limit,
                    "sort_by": search_params.sort_by,
                    "sort_order": search_params.sort_order
                }
            )

            result = await self.tag_library_service.get_all_tags(search_params)

            logger.info(
                "获取所有标签完成",
                extra={
                    "total": result["total"],
                    "page": result["page"],
                    "limit": result["limit"]
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取所有标签失败",
                extra={
                    "search_params": search_params.model_dump(),
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取所有标签失败: {str(e)}"
            ) from e

    async def handle_get_popular_tags(self, limit: int = 10) -> Dict[str, Any]:
        """处理获取热门标签请求"""
        try:
            logger.info(
                "处理获取热门标签请求",
                extra={
                    "limit": limit
                }
            )

            result = await self.tag_library_service.get_popular_tags(limit)

            logger.info(
                "获取热门标签完成",
                extra={
                    "limit": limit,
                    "total": result["total"]
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取热门标签失败",
                extra={
                    "limit": limit,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取热门标签失败: {str(e)}"
            ) from e

    async def handle_create_tag(self, tag_data: TagCreate) -> Dict[str, Any]:
        """处理创建标签请求"""
        try:
            logger.info(
                "处理创建标签请求",
                extra={
                    "tag_name": tag_data.name,
                    "description": tag_data.description
                }
            )

            result = await self.tag_library_service.create_tag(tag_data)

            logger.info(
                "创建标签成功",
                extra={
                    "tag_name": tag_data.name,
                    "tag_id": result["tag"]["id"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "创建标签失败 - 业务错误",
                extra={
                    "tag_name": tag_data.name,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "创建标签失败 - 系统错误",
                extra={
                    "tag_name": tag_data.name,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建标签失败: {str(e)}"
            ) from e

    async def handle_delete_tag(self, tag_name: str) -> Dict[str, Any]:
        """处理删除标签请求"""
        try:
            logger.info(
                "处理删除标签请求",
                extra={
                    "tag_name": tag_name
                }
            )

            result = await self.tag_library_service.delete_tag(tag_name)

            logger.info(
                "删除标签成功",
                extra={
                    "tag_name": tag_name
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "删除标签失败 - 业务错误",
                extra={
                    "tag_name": tag_name,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "删除标签失败 - 系统错误",
                extra={
                    "tag_name": tag_name,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除标签失败: {str(e)}"
            ) from e

    async def handle_search_tags(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """处理搜索标签请求"""
        try:
            logger.info(
                "处理搜索标签请求",
                extra={
                    "query": query,
                    "limit": limit
                }
            )

            result = await self.tag_library_service.search_tags(query, limit)

            logger.info(
                "搜索标签完成",
                extra={
                    "query": query,
                    "total": result["total"]
                }
            )

            return result

        except Exception as e:
            logger.error(
                "搜索标签失败",
                extra={
                    "query": query,
                    "limit": limit,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"搜索标签失败: {str(e)}"
            ) from e