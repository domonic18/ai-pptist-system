"""
标签服务
处理标签相关的核心业务逻辑
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.repositories.tag import TagRepository
from app.schemas.tag import ImageTagUpdate, ImageTagAdd, TagCreate, TagSearchParams, BatchImageTagOperation, BatchImageTagResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class TagService:
    """标签服务 - 处理标签相关的核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.image_repo = ImageRepository(db)
        self.tag_repo = TagRepository(db)

    async def get_image_tags(self, image_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取图片标签

        Args:
            image_id: 图片ID
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 图片标签信息

        Raises:
            ValueError: 图片不存在或无权限访问
        """
        # 获取图片
        image = await self.image_repo.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"图片不存在: {image_id}")

        # 检查权限
        if image.user_id != user_id:
            raise ValueError("无权访问该图片")

        return {
            "image_id": image_id,
            "tags": image.tags or [],
            "total": len(image.tags or [])
        }

    async def add_image_tags(
        self,
        image_id: str,
        user_id: str,
        tag_data: ImageTagAdd
    ) -> Dict[str, Any]:
        """
        添加图片标签

        Args:
            image_id: 图片ID
            user_id: 用户ID
            tag_data: 标签数据

        Returns:
            Dict[str, Any]: 更新后的图片标签信息

        Raises:
            ValueError: 图片不存在或无权限修改
        """
        logger.info(f"开始为图片 {image_id} 添加标签: {tag_data.tags}")

        # 获取图片
        image = await self.image_repo.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"图片不存在: {image_id}")

        # 检查权限
        if image.user_id != user_id:
            raise ValueError("无权修改该图片")

        # 获取当前标签
        current_tags = image.tags or []
        logger.info(f"图片 {image_id} 当前标签: {current_tags}")

        # 去重并添加新标签
        new_tags = list(set(current_tags + tag_data.tags))
        logger.info(f"合并后的新标签: {new_tags}")

        # 更新图片标签
        update_data = {"tags": new_tags}
        updated_image = await self.image_repo.update_image(image_id, update_data)

        logger.info(f"数据库更新结果: {updated_image is not None}")
        if updated_image:
            logger.info(f"更新后的图片标签: {updated_image.tags}")
            # 创建或获取标签，并增加使用次数
            await self.tag_repo.create_or_get_tags(tag_data.tags)
            await self.tag_repo.increment_tag_usage(tag_data.tags)
        else:
            logger.warning(f"图片 {image_id} 更新失败，返回None")

        result = {
            "image_id": image_id,
            "added_tags": tag_data.tags,
            "current_tags": updated_image.tags if updated_image else new_tags,
            "total": len(updated_image.tags) if updated_image else len(new_tags)
        }
        logger.info(f"添加标签操作完成，返回结果: {result}")
        return result

    async def update_image_tags(
        self,
        image_id: str,
        user_id: str,
        tag_data: ImageTagUpdate
    ) -> Dict[str, Any]:
        """
        更新图片标签

        Args:
            image_id: 图片ID
            user_id: 用户ID
            tag_data: 标签更新数据

        Returns:
            Dict[str, Any]: 更新后的图片标签信息

        Raises:
            ValueError: 图片不存在或无权限修改
        """
        # 获取图片
        image = await self.image_repo.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"图片不存在: {image_id}")

        # 检查权限
        if image.user_id != user_id:
            raise ValueError("无权修改该图片")

        # 获取旧标签用于统计更新
        old_tags = image.tags or []
        new_tags = list(set(tag_data.tags))  # 去重

        # 计算标签变化
        added_tags = list(set(new_tags) - set(old_tags))
        removed_tags = list(set(old_tags) - set(new_tags))

        # 更新图片标签
        update_data = {"tags": new_tags}
        updated_image = await self.image_repo.update_image(image_id, update_data)

        if updated_image:
            # 处理标签统计
            if added_tags:
                await self.tag_repo.create_or_get_tags(added_tags)
                await self.tag_repo.increment_tag_usage(added_tags)

            if removed_tags:
                await self.tag_repo.decrement_tag_usage(removed_tags)

        return {
            "image_id": image_id,
            "added_tags": added_tags,
            "removed_tags": removed_tags,
            "current_tags": updated_image.tags if updated_image else new_tags,
            "total": len(updated_image.tags) if updated_image else len(new_tags)
        }

    async def delete_image_tags(
        self,
        image_id: str,
        user_id: str,
        tags_to_delete: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        删除图片标签

        Args:
            image_id: 图片ID
            user_id: 用户ID
            tags_to_delete: 要删除的标签列表，None表示删除所有标签

        Returns:
            Dict[str, Any]: 更新后的图片标签信息

        Raises:
            ValueError: 图片不存在或无权限修改
        """
        # 获取图片
        image = await self.image_repo.get_image_by_id(image_id)
        if not image:
            raise ValueError(f"图片不存在: {image_id}")

        # 检查权限
        if image.user_id != user_id:
            raise ValueError("无权修改该图片")

        current_tags = image.tags or []

        if tags_to_delete:
            # 删除指定标签
            new_tags = [tag for tag in current_tags if tag not in tags_to_delete]
            removed_tags = list(set(tags_to_delete) & set(current_tags))
        else:
            # 删除所有标签
            new_tags = []
            removed_tags = current_tags

        # 更新图片标签
        update_data = {"tags": new_tags}
        updated_image = await self.image_repo.update_image(image_id, update_data)

        if updated_image and removed_tags:
            # 减少标签使用次数
            await self.tag_repo.decrement_tag_usage(removed_tags)

        return {
            "image_id": image_id,
            "removed_tags": removed_tags,
            "current_tags": updated_image.tags if updated_image else new_tags,
            "total": len(updated_image.tags) if updated_image else len(new_tags)
        }

    async def search_images_by_tags(
        self,
        user_id: str,
        tags: List[str],
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        根据标签搜索图片

        Args:
            user_id: 用户ID
            tags: 标签列表
            skip: 跳过的记录数
            limit: 返回的记录数

        Returns:
            Dict[str, Any]: 搜索结果
        """
        # 获取用户的所有图片
        images, total = await self.image_repo.get_user_images(user_id, skip=0, limit=1000)

        # 根据标签过滤图片
        filtered_images = []
        for image in images:
            image_tags = image.tags or []
            # 检查图片是否包含所有指定的标签
            if all(tag in image_tags for tag in tags):
                filtered_images.append(image)

        # 应用分页
        paginated_images = filtered_images[skip:skip + limit]

        return {
            "items": [image.to_dict() for image in paginated_images],
            "total": len(filtered_images),
            "skip": skip,
            "limit": limit,
            "query_tags": tags
        }

    async def get_all_tags(
        self,
        search_params: TagSearchParams
    ) -> Dict[str, Any]:
        """
        获取所有标签

        Args:
            search_params: 搜索参数

        Returns:
            Dict[str, Any]: 标签列表
        """
        skip = (search_params.page - 1) * search_params.limit
        tags, total = await self.tag_repo.get_all_tags(
            skip=skip,
            limit=search_params.limit,
            query=search_params.query,
            sort_by=search_params.sort_by,
            sort_order=search_params.sort_order
        )

        return {
            "items": [tag.to_dict() for tag in tags],
            "total": total,
            "page": search_params.page,
            "limit": search_params.limit,
            "total_pages": (total + search_params.limit - 1) // search_params.limit
        }

    async def get_popular_tags(self, limit: int = 10) -> Dict[str, Any]:
        """
        获取热门标签

        Args:
            limit: 返回的标签数量

        Returns:
            Dict[str, Any]: 热门标签列表
        """
        tags = await self.tag_repo.get_popular_tags(limit)

        return {
            "tags": [tag.to_dict() for tag in tags],
            "total": len(tags),
            "limit": limit
        }

    async def create_tag(self, tag_data: TagCreate) -> Dict[str, Any]:
        """
        创建标签

        Args:
            tag_data: 标签创建数据

        Returns:
            Dict[str, Any]: 创建的标签信息

        Raises:
            ValueError: 标签已存在
        """
        # 检查标签是否已存在
        existing_tag = await self.tag_repo.get_tag_by_name(tag_data.name)
        if existing_tag:
            raise ValueError(f"标签 '{tag_data.name}' 已存在")

        # 创建标签
        tag = await self.tag_repo.create_tag(
            name=tag_data.name,
            description=tag_data.description
        )

        return {
            "tag": tag.to_dict(),
            "message": f"标签 '{tag_data.name}' 创建成功"
        }

    async def delete_tag(self, tag_name: str) -> Dict[str, Any]:
        """
        删除标签

        Args:
            tag_name: 标签名称

        Returns:
            Dict[str, Any]: 删除结果

        Raises:
            ValueError: 标签不存在或删除失败
        """
        # 检查标签是否存在
        tag = await self.tag_repo.get_tag_by_name(tag_name)
        if not tag:
            raise ValueError(f"标签 '{tag_name}' 不存在")

        # 删除标签
        success = await self.tag_repo.delete_tag_by_name(tag_name)

        if success:
            return {
                "message": f"标签 '{tag_name}' 删除成功",
                "deleted_tag": tag_name
            }
        else:
            raise ValueError(f"删除标签 '{tag_name}' 失败")

    async def search_tags(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        搜索标签

        Args:
            query: 搜索查询
            limit: 返回的标签数量

        Returns:
            Dict[str, Any]: 搜索结果
        """
        tags, total = await self.tag_repo.get_all_tags(
            skip=0,
            limit=limit,
            query=query,
            sort_by="usage_count",
            sort_order="desc"
        )

        return {
            "tags": [tag.to_dict() for tag in tags],
            "total": total,
            "query": query,
            "limit": limit
        }

    async def batch_operate_image_tags(self, batch_data: BatchImageTagOperation, user_id: str) -> BatchImageTagResponse:
        """
        批量操作图片标签

        Args:
            batch_data: 批量操作数据
            user_id: 用户ID

        Returns:
            BatchImageTagResponse: 批量操作结果
        """
        success_count = 0
        failed_count = 0
        results = []
        errors = []

        logger.info(f"开始批量操作图片标签，图片数量: {len(batch_data.image_ids)}, 操作类型: {batch_data.operation}, 标签: {batch_data.tags}")

        for image_id in batch_data.image_ids:
            try:
                logger.info(f"处理图片 ID: {image_id}")

                # 验证图片是否存在且用户有权限
                image = await self.image_repo.get_image_by_id(image_id)
                if not image:
                    logger.warning(f"图片不存在: {image_id}")
                    errors.append({
                        "image_id": image_id,
                        "error": "图片不存在"
                    })
                    failed_count += 1
                    continue

                logger.info(f"图片存在，当前标签: {image.tags}, 用户ID: {image.user_id}")

                if image.user_id != user_id:
                    logger.warning(f"用户无权修改图片 {image_id}, 图片用户: {image.user_id}, 请求用户: {user_id}")
                    errors.append({
                        "image_id": image_id,
                        "error": "无权修改该图片"
                    })
                    failed_count += 1
                    continue

                # 根据操作类型执行相应操作
                if batch_data.operation == "add":
                    logger.info(f"为图片 {image_id} 添加标签: {batch_data.tags}")
                    result = await self.add_image_tags(image_id, user_id, ImageTagAdd(tags=batch_data.tags))
                elif batch_data.operation == "remove":
                    logger.info(f"从图片 {image_id} 删除标签: {batch_data.tags}")
                    result = await self.delete_image_tags(image_id, user_id, batch_data.tags)
                elif batch_data.operation == "replace":
                    logger.info(f"替换图片 {image_id} 标签为: {batch_data.tags}")
                    result = await self.update_image_tags(image_id, user_id, ImageTagUpdate(tags=batch_data.tags))
                else:
                    raise ValueError(f"不支持的操作类型: {batch_data.operation}")

                logger.info(f"图片 {image_id} 操作成功，结果: {result}")
                # 简化结果结构，避免潜在的序列化问题
                results.append({
                    "image_id": image_id,
                    "operation": batch_data.operation,
                    "current_tags": result.get("current_tags", []),
                    "total": result.get("total", 0)
                })
                success_count += 1

            except Exception as e:
                logger.error(f"处理图片 {image_id} 时发生错误: {str(e)}")
                errors.append({
                    "image_id": image_id,
                    "error": str(e)
                })
                failed_count += 1

        logger.info(f"批量操作完成，成功: {success_count}, 失败: {failed_count}")
        return BatchImageTagResponse(
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            errors=errors
        )