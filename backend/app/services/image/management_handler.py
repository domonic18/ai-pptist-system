"""
图片管理业务处理器
处理图片的CRUD操作
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.management_service import ManagementService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ManagementHandler:
    """图片管理业务处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.management_service = ManagementService(db)

    async def handle_list_images(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """处理获取图片列表请求"""
        try:
            logger.info(
                "处理获取图片列表",
                extra={
                    "user_id": user_id,
                    "skip": skip,
                    "limit": limit
                }
            )

            result = await self.management_service.list_images(user_id, skip, limit)

            logger.info(
                "获取图片列表成功",
                extra={
                    "total": result["total"],
                    "returned": len(result["items"])
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取图片列表失败",
                extra={
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取图片列表失败: {str(e)}"
            )

    async def handle_get_image_detail(
        self,
        image_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """处理获取图片详情请求"""
        try:
            logger.info(
                "处理获取图片详情",
                extra={
                    "image_id": image_id,
                    "user_id": user_id
                }
            )

            image_detail = await self.management_service.get_image_detail(image_id, user_id)

            if not image_detail:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="图片不存在"
                )

            logger.info(
                "获取图片详情成功",
                extra={
                    "image_id": image_id
                }
            )

            return image_detail

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "获取图片详情失败",
                extra={
                    "image_id": image_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取图片详情失败: {str(e)}"
            )

    async def handle_delete_image(
        self,
        image_id: str,
        user_id: str
    ) -> bool:
        """处理删除图片请求"""
        try:
            logger.info(
                "处理删除图片",
                extra={
                    "image_id": image_id,
                    "user_id": user_id
                }
            )

            success = await self.management_service.delete_image(image_id, user_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="图片不存在或删除失败"
                )

            logger.info(
                "删除图片成功",
                extra={
                    "image_id": image_id
                }
            )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "删除图片失败",
                extra={
                    "image_id": image_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除图片失败: {str(e)}"
            )

    async def handle_update_image_info(
        self,
        image_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理更新图片信息请求"""
        try:
            logger.info(
                "处理更新图片信息",
                extra={
                    "image_id": image_id,
                    "user_id": user_id
                }
            )

            result = await self.management_service.update_image_info(
                image_id, user_id, update_data
            )

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="图片不存在或更新失败"
                )

            logger.info(
                "更新图片信息成功",
                extra={
                    "image_id": image_id
                }
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "更新图片信息失败",
                extra={
                    "image_id": image_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新图片信息失败: {str(e)}"
            )

    async def handle_get_image_access_url(
        self,
        image_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """处理获取图片访问URL请求"""
        try:
            logger.info(
                "处理获取图片访问URL",
                extra={
                    "image_id": image_id,
                    "user_id": user_id
                }
            )

            image_detail = await self.management_service.get_image_detail(image_id, user_id)

            if not image_detail:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="图片不存在"
                )

            # 返回包含URL的响应
            result = {
                "image_id": image_id,
                "url": image_detail["url"],
                "storage_type": "cos_presigned" if image_detail["cos_key"] else "direct"
            }

            logger.info(
                "获取图片访问URL成功",
                extra={
                    "image_id": image_id
                }
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "获取图片访问URL失败",
                extra={
                    "image_id": image_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取图片访问URL失败: {str(e)}"
            )

    async def handle_get_image_generation_history(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """处理获取图片生成历史请求"""
        try:
            logger.info(
                "处理获取图片生成历史",
                extra={
                    "user_id": user_id,
                    "page": page,
                    "limit": limit
                }
            )

            result = await self.management_service.get_image_generation_history(
                user_id=user_id,
                page=page,
                limit=limit
            )

            logger.info(
                "获取图片生成历史成功",
                extra={
                    "total": result.get("total", 0),
                    "returned": len(result.get("items", []))
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取图片生成历史失败",
                extra={
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取图片生成历史失败: {str(e)}"
            )