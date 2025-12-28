"""
图片标签管理业务处理器
处理图片标签和标签管理的网络请求、日志记录和异常处理
"""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.tagging.service import TaggingService
from app.schemas.image_tagging import ImageTagUpdate, ImageTagAdd, ImageTagDelete, BatchImageTagOperation
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageTaggingHandler:
    """图片标签处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tagging_service = TaggingService(db)

    async def handle_get_image_tags(self, image_id: str, user_id: str) -> Dict[str, Any]:
        """处理获取图片标签请求"""
        try:
            logger.info(
                "处理获取图片标签请求",
                extra={
                    "image_id": image_id,
                    "user_id": user_id
                }
            )

            result = await self.tagging_service.get_image_tags(image_id, user_id)

            logger.info(
                "获取图片标签成功",
                extra={
                    "image_id": image_id,
                    "tags_count": result["total"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "获取图片标签失败 - 业务错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "获取图片标签失败 - 系统错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取图片标签失败: {str(e)}"
            ) from e

    async def handle_add_image_tags(
        self,
        image_id: str,
        user_id: str,
        tag_data: ImageTagAdd
    ) -> Dict[str, Any]:
        """处理添加图片标签请求"""
        try:
            logger.info(
                "处理添加图片标签请求",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags
                }
            )

            result = await self.tagging_service.add_image_tags(image_id, user_id, tag_data)

            logger.info(
                "添加图片标签成功",
                extra={
                    "image_id": image_id,
                    "added_tags": result["added_tags"],
                    "current_tags_count": result["total"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "添加图片标签失败 - 业务错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "添加图片标签失败 - 系统错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"添加图片标签失败: {str(e)}"
            ) from e

    async def handle_update_image_tags(
        self,
        image_id: str,
        user_id: str,
        tag_data: ImageTagUpdate
    ) -> Dict[str, Any]:
        """处理更新图片标签请求"""
        try:
            logger.info(
                "处理更新图片标签请求",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags
                }
            )

            result = await self.tagging_service.update_image_tags(image_id, user_id, tag_data)

            logger.info(
                "更新图片标签成功",
                extra={
                    "image_id": image_id,
                    "added_tags": result["added_tags"],
                    "removed_tags": result["removed_tags"],
                    "current_tags_count": result["total"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "更新图片标签失败 - 业务错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "更新图片标签失败 - 系统错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags": tag_data.tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新图片标签失败: {str(e)}"
            ) from e

    async def handle_delete_image_tags(
        self,
        image_id: str,
        user_id: str,
        tags_to_delete: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """处理删除图片标签请求"""
        try:
            logger.info(
                "处理删除图片标签请求",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags_to_delete": tags_to_delete or "ALL"
                }
            )

            result = await self.tagging_service.delete_image_tags(image_id, user_id, tags_to_delete)

            logger.info(
                "删除图片标签成功",
                extra={
                    "image_id": image_id,
                    "removed_tags": result["removed_tags"],
                    "current_tags_count": result["total"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "删除图片标签失败 - 业务错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags_to_delete": tags_to_delete,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "删除图片标签失败 - 系统错误",
                extra={
                    "image_id": image_id,
                    "user_id": user_id,
                    "tags_to_delete": tags_to_delete,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除图片标签失败: {str(e)}"
            ) from e

    async def handle_search_images_by_tags(
        self,
        user_id: str,
        tags: List[str],
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """处理根据标签搜索图片请求"""
        try:
            logger.info(
                "处理根据标签搜索图片请求",
                extra={
                    "user_id": user_id,
                    "tags": tags,
                    "skip": skip,
                    "limit": limit
                }
            )

            result = await self.tagging_service.search_images_by_tags(user_id, tags, skip, limit)

            logger.info(
                "根据标签搜索图片完成",
                extra={
                    "user_id": user_id,
                    "tags": tags,
                    "results_count": result["total"]
                }
            )

            return result

        except Exception as e:
            logger.error(
                "根据标签搜索图片失败",
                extra={
                    "user_id": user_id,
                    "tags": tags,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"根据标签搜索图片失败: {str(e)}"
            ) from e

    async def handle_batch_operate_image_tags(
        self,
        batch_data: BatchImageTagOperation,
        user_id: str
    ) -> Dict[str, Any]:
        """处理批量操作图片标签请求"""
        try:
            logger.info(
                "处理批量操作图片标签请求",
                extra={
                    "user_id": user_id,
                    "image_count": len(batch_data.image_ids),
                    "tags": batch_data.tags,
                    "operation": batch_data.operation
                }
            )

            result = await self.tagging_service.batch_operate_image_tags(batch_data, user_id)

            logger.info(
                "批量操作图片标签完成",
                extra={
                    "user_id": user_id,
                    "success_count": result.success_count,
                    "failed_count": result.failed_count,
                    "operation": batch_data.operation
                }
            )

            return result.model_dump()

        except ValueError as e:
            logger.warning(
                "批量操作图片标签失败 - 业务错误",
                extra={
                    "user_id": user_id,
                    "operation": batch_data.operation,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "批量操作图片标签失败 - 系统错误",
                extra={
                    "user_id": user_id,
                    "operation": batch_data.operation,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"批量操作图片标签失败: {str(e)}"
            ) from e