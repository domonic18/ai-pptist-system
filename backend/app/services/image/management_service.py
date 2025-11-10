"""
图片管理服务
处理图片的CRUD操作
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.core.storage import get_storage_service
from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ManagementService:
    """图片管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ImageRepository(db)
        self.storage_service = get_storage_service()

    async def list_images(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取用户图片列表"""
        try:
            images, total = await self.repository.get_user_images(user_id, skip, limit)

            # 为每个图片生成访问URL
            images_with_urls = []
            for image in images:
                image_dict = {
                    "id": image.id,
                    "original_filename": image.original_filename,
                    "file_size": image.file_size,
                    "mime_type": image.mime_type,
                    "description": image.description,
                    "tags": image.tags,
                    "created_at": image.created_at,
                    "url": await self._generate_access_url(image),
                    "source_type": image.source_type,
                    "model_name": image.generation_model,
                    "cos_key": image.cos_key,
                    "cos_bucket": image.cos_bucket,
                    "cos_region": image.cos_region,
                    "width": image.width,
                    "height": image.height
                }
                images_with_urls.append(image_dict)

            return {
                "items": images_with_urls,
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            }

        except Exception as e:
            logger.error(f"获取图片列表失败: {e}")
            raise

    async def get_image_detail(
        self,
        image_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取图片详情"""
        try:
            image = await self.repository.get_image_by_id(image_id)
            if not image or image.user_id != user_id:
                return None

            return {
                "id": image.id,
                "original_filename": image.original_filename,
                "file_size": image.file_size,
                "mime_type": image.mime_type,
                "description": image.description,
                "tags": image.tags,
                "created_at": image.created_at,
                "url": await self._generate_access_url(image),
                "cos_key": image.cos_key,
                "storage_status": image.storage_status,
                "source_type": image.source_type,
                "model_name": image.generation_model,
                "cos_bucket": image.cos_bucket,
                "cos_region": image.cos_region,
                "width": image.width,
                "height": image.height
            }

        except Exception as e:
            logger.error(f"获取图片详情失败: {e}")
            raise

    async def delete_image(
        self,
        image_id: str,
        user_id: str
    ) -> bool:
        """删除图片"""
        try:
            # 验证图片所有权
            image = await self.repository.get_image_by_id(image_id)
            if not image or image.user_id != user_id:
                return False

            # 如果图片存储在COS，尝试删除COS文件
            if image.cos_key:
                try:
                    await self.storage_service.delete(image.cos_key)
                except Exception as e:
                    logger.warning(f"删除COS文件失败: {e}")

            # 删除数据库记录
            return await self.repository.delete_image(image_id)

        except Exception as e:
            logger.error(f"删除图片失败: {e}")
            raise

    async def update_image_info(
        self,
        image_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新图片信息"""
        try:
            # 验证图片所有权
            image = await self.repository.get_image_by_id(image_id)
            if not image or image.user_id != user_id:
                return None

            # 只允许更新特定字段
            allowed_fields = {"description", "tags", "is_public"}
            filtered_data = {
                k: v for k, v in update_data.items()
                if k in allowed_fields and hasattr(image, k)
            }

            if not filtered_data:
                return None

            # 更新记录
            updated_image = await self.repository.update_image(image_id, filtered_data)
            if not updated_image:
                return None

            return {
                "id": updated_image.id,
                "description": updated_image.description,
                "tags": updated_image.tags,
                "is_public": updated_image.is_public
            }

        except Exception as e:
            logger.error(f"更新图片信息失败: {e}")
            raise

    async def _generate_access_url(self, image) -> str:
        """为图片生成访问URL - 集成Redis缓存"""
        try:
            if image.cos_key:
                # 使用带缓存的图片URL服务，优先从Redis缓存获取
                try:
                    from app.services.cache.image_url_service import get_image_url_service

                    service = await get_image_url_service()
                    url, metadata = await service.get_image_url(
                        image_key=image.cos_key,
                        force_refresh=False,
                        use_cache=True
                    )

                    # 记录缓存命中情况
                    if metadata.get("from_cache", False):
                        logger.debug(
                            "从Redis缓存获取图片URL",
                            extra={
                                "image_id": image.id,
                                "cos_key": image.cos_key
                            }
                        )

                    return url

                except Exception as cache_error:
                    # 缓存失败时降级到直接调用COS API
                    logger.warning(
                        f"缓存服务失败，降级到直接生成URL: {str(cache_error)}",
                        extra={
                            "image_id": image.id,
                            "cos_key": image.cos_key,
                            "error": str(cache_error)
                        }
                    )

                    # 降级到直接调用COS API
                    return await self.storage_service.generate_url(
                        image.cos_key, settings.cos_url_expires, "get"
                    )

            elif image.image_url:
                # 使用直接URL（通常是外部URL，不需要缓存）
                return image.image_url
            else:
                # 没有可用的URL
                return ""

        except Exception as e:
            logger.error(
                f"生成访问URL失败: {e}",
                extra={"image_id": getattr(image, "id", "unknown")}
            )
            return ""

    async def get_image_generation_history(
        self, user_id: Optional[str] = None, page: int = 1, limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取图片生成历史记录

        Args:
            user_id: 用户ID，如果为None则获取所有历史记录
            page: 页码，默认为1
            limit: 每页数量，默认为20

        Returns:
            Dict[str, Any]: 历史记录数据
        """
        try:
            logger.info("获取图片生成历史记录", extra={
                "user_id": user_id,
                "page": page,
                "limit": limit
            })

            # TODO: 实现实际的数据库查询逻辑
            # 这里暂时返回模拟数据，实际应该查询数据库中的图片生成记录
            # 可能需要在数据库中创建一个图片生成历史表

            # 模拟数据
            mock_history = []
            for i in range(min(limit, 5)):  # 模拟最多5条记录
                mock_history.append({
                    "id": f"gen_{i + 1}",
                    "prompt": f"Generated image prompt {i + 1}",
                    "model_name": "google/gemini-2.5-pro",
                    "image_url": f"https://example.com/generated_image_{i + 1}.jpg",
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00Z",
                    "user_id": user_id or "anonymous"
                })

            # 计算分页
            total = 5  # 模拟总数
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_history = mock_history[start_idx:end_idx]

            return {
                "page": page,
                "limit": limit,
                "total": total,
                "items": paginated_history,
                "message": "历史记录功能尚未完全实现，当前为模拟数据"
            }

        except Exception as e:
            logger.error("获取图片生成历史记录失败", extra={"error": str(e)})
            return {
                "page": page,
                "limit": limit,
                "total": 0,
                "items": [],
                "message": f"获取历史记录失败: {str(e)}"
            }