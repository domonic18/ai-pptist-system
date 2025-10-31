"""
图片数据访问层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, desc, update
from sqlalchemy.sql.functions import count

from app.models.image import Image
from app.schemas.image_manager import ImageCreate
from .base import BaseRepository


class ImageRepository(BaseRepository):
    """图片Repository"""

    @property
    def model(self):
        return Image


    async def create_image(
        self,
        create_data: ImageCreate,
        user_id: str
    ) -> Image:
        """创建图片记录"""

        # 使用基类的create方法，它会自动生成ID
        return await self.create(
            user_id=user_id,
            prompt=getattr(create_data, 'prompt', None),
            image_url=getattr(create_data, 'image_url', None),
            generation_model=getattr(create_data, 'generation_model', 'user_upload'),
            width=getattr(create_data, 'width', None),
            height=getattr(create_data, 'height', None),
            file_size=getattr(create_data, 'file_size', 0),
            mime_type=getattr(create_data, 'mime_type', 'image/jpeg'),
            cos_key=getattr(create_data, 'cos_key', None),
            cos_bucket=getattr(create_data, 'cos_bucket', None),
            cos_region=getattr(create_data, 'cos_region', None),
            source_type=getattr(create_data, 'source_type', 'uploaded'),
            original_filename=getattr(create_data, 'original_filename', None),
            description=getattr(create_data, 'description', None),
            tags=getattr(create_data, 'tags', []),
            is_public=getattr(create_data, 'is_public', False),
            storage_status=getattr(create_data, 'storage_status', 'active')
        )

    async def get_image_by_id(self, image_id: str) -> Optional[Image]:
        """根据ID获取图片"""
        stmt = select(Image).where(Image.id == image_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_image_by_cos_key(self, cos_key: str) -> Optional[Image]:
        """根据COS key获取图片"""
        stmt = select(Image).where(Image.cos_key == cos_key)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_image(self, image_id: str, update_data: Dict[str, Any]) -> Optional[Image]:
        """更新图片记录"""
        stmt = (
            update(Image)
            .where(Image.id == image_id)
            .values(**update_data)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            # 返回更新后的记录
            return await self.get_image_by_id(image_id)
        return None

    async def delete_image(self, image_id: str) -> bool:
        """删除图片记录"""
        stmt = delete(Image).where(Image.id == image_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_user_images(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Image], int]:
        """获取用户的图片列表"""
        # 构建查询条件
        stmt = (
            select(Image)
            .where(Image.user_id == user_id)
            .order_by(desc(Image.created_at))
            .offset(skip)
            .limit(limit)
        )

        count_stmt = select(count(Image.id)).where(Image.user_id == user_id)

        # 执行查询
        result = await self.db.execute(stmt)
        images = result.scalars().all()

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(images), total

    async def get_user_image_count(self, user_id: str) -> int:
        """获取用户图片总数"""
        stmt = select(count(Image.id)).where(Image.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def search_by_prompt(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Image]:
        """根据提示词搜索图片"""
        stmt = select(Image).where(
            Image.prompt.ilike(f"%{query}%") |
            Image.description.ilike(f"%{query}%") |
            Image.original_filename.ilike(f"%{query}%")
        )

        # 如果指定了用户ID，添加用户过滤
        if user_id:
            stmt = stmt.where(Image.user_id == user_id)

        # 按创建时间排序，限制数量
        stmt = stmt.order_by(desc(Image.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_cos_stored_images(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Image], int]:
        """获取COS存储的图片列表"""
        # 构建查询条件：有COS信息的图片
        stmt = (
            select(Image)
            .where(Image.cos_key.isnot(None))
            .where(Image.cos_bucket.isnot(None))
            .where(Image.cos_region.isnot(None))
        )

        # 如果指定了用户ID，添加用户过滤
        if user_id:
            stmt = stmt.where(Image.user_id == user_id)

        # 按创建时间排序
        stmt = stmt.order_by(desc(Image.created_at)).offset(skip).limit(limit)

        # 执行查询
        result = await self.db.execute(stmt)
        images = result.scalars().all()

        # 构建计数查询
        count_stmt = (
            select(count(Image.id))
            .where(Image.cos_key.isnot(None))
            .where(Image.cos_bucket.isnot(None))
            .where(Image.cos_region.isnot(None))
        )

        if user_id:
            count_stmt = count_stmt.where(Image.user_id == user_id)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(images), total

    async def update_cos_info(
        self,
        image_id: str,
        cos_key: str,
        cos_bucket: str,
        cos_region: str
    ) -> Optional[Image]:
        """更新图片的COS信息"""
        update_data = {
            'cos_key': cos_key,
            'cos_bucket': cos_bucket,
            'cos_region': cos_region
        }

        return await self.update_image(image_id, update_data)

    async def get_images_by_source_type(
        self,
        source_type: str,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Image], int]:
        """根据来源类型获取图片列表"""
        # 构建查询条件
        stmt = select(Image).where(Image.source_type == source_type)

        # 如果指定了用户ID，添加用户过滤
        if user_id:
            stmt = stmt.where(Image.user_id == user_id)

        # 按创建时间排序
        stmt = stmt.order_by(desc(Image.created_at)).offset(skip).limit(limit)

        # 执行查询
        result = await self.db.execute(stmt)
        images = result.scalars().all()

        # 构建计数查询
        count_stmt = select(count(Image.id)).where(Image.source_type == source_type)

        if user_id:
            count_stmt = count_stmt.where(Image.user_id == user_id)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(images), total

    async def search_images_by_tags(
        self,
        tags: List[str],
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Image], int]:
        """根据标签搜索图片"""
        # 构建查询条件：包含任一标签的图片
        conditions = []
        for tag in tags:
            conditions.append(Image.tags.any(tag))

        if not conditions:
            return [], 0

        stmt = select(Image).where(*conditions)

        # 如果指定了用户ID，添加用户过滤
        if user_id:
            stmt = stmt.where(Image.user_id == user_id)

        # 按创建时间排序
        stmt = stmt.order_by(desc(Image.created_at)).offset(skip).limit(limit)

        # 执行查询
        result = await self.db.execute(stmt)
        images = result.scalars().all()

        # 构建计数查询
        count_stmt = select(count(Image.id)).where(*conditions)

        if user_id:
            count_stmt = count_stmt.where(Image.user_id == user_id)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(images), total
