"""
图片搜索业务处理器
处理图片搜索相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.search_service import ImageSearchService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageSearchHandler:
    """图片搜索业务处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_service = ImageSearchService(db)

    async def handle_search_images(
        self,
        query: str,
        user_id: str,
        limit: int = 20,
        match_threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """处理搜索图片请求"""
        try:
            logger.info(
                "处理搜索图片",
                extra={
                    "query": query,
                    "user_id": user_id,
                    "limit": limit
                }
            )

            search_result = await self.search_service.search_images(query, user_id, limit, match_threshold)

            logger.info(
                "搜索图片完成",
                extra={
                    "query": query,
                    "results_count": search_result["total"]
                }
            )

            return search_result

        except Exception as e:
            logger.error(
                "搜索图片失败",
                extra={
                    "query": query,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"搜索图片失败: {str(e)}"
            )

    async def handle_search_by_tags(
        self,
        tags: List[str],
        user_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """处理按标签搜索图片请求"""
        try:
            logger.info(
                "处理按标签搜索图片",
                extra={
                    "tags": tags,
                    "user_id": user_id,
                    "limit": limit
                }
            )

            search_result = await self.search_service.search_by_tags(tags, user_id, limit)

            logger.info(
                "按标签搜索完成",
                extra={
                    "tags": tags,
                    "results_count": search_result["total"]
                }
            )

            return search_result

        except Exception as e:
            logger.error(
                "按标签搜索失败",
                extra={
                    "tags": tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"按标签搜索失败: {str(e)}"
            )

    async def handle_get_user_tags(
        self,
        user_id: str
    ) -> List[str]:
        """处理获取用户标签请求"""
        try:
            logger.info(
                "处理获取用户标签",
                extra={
                    "user_id": user_id
                }
            )

            tags = await self.search_service.get_user_tags(user_id)

            logger.info(
                "获取用户标签完成",
                extra={
                    "user_id": user_id,
                    "tags_count": len(tags)
                }
            )

            return tags

        except Exception as e:
            logger.error(
                "获取用户标签失败",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取用户标签失败: {str(e)}"
            )

    async def handle_get_search_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """处理获取搜索统计信息请求"""
        try:
            logger.info(
                "处理获取搜索统计信息",
                extra={
                    "user_id": user_id
                }
            )

            # 获取用户标签
            tags = await self.search_service.get_user_tags(user_id)

            # 获取图片总数
            from app.repositories.image import ImageRepository
            repository = ImageRepository(self.db)
            total_images = await repository.get_user_image_count(user_id)

            statistics = {
                "total_images": total_images,
                "unique_tags": len(tags),
                "tags_list": tags[:10],  # 只返回前10个标签
                "has_search_history": False  # 暂时不支持搜索历史
            }

            logger.info(
                "获取搜索统计信息完成",
                extra={
                    "user_id": user_id,
                    "total_images": total_images
                }
            )

            return statistics

        except Exception as e:
            logger.error(
                "获取搜索统计信息失败",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取搜索统计信息失败: {str(e)}"
            )