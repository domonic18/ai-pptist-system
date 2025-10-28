"""
标签数据访问层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, desc, update, func, and_
from sqlalchemy.sql.functions import count

from app.models.tag import Tag
from .base import BaseRepository


class TagRepository(BaseRepository):
    """标签Repository"""

    @property
    def model(self):
        return Tag

    async def create_tag(self, name: str, description: Optional[str] = None) -> Tag:
        """创建标签"""
        return await self.create(
            name=name,
            description=description
        )

    async def get_tag_by_id(self, tag_id: str) -> Optional[Tag]:
        """根据ID获取标签"""
        stmt = select(Tag).where(Tag.id == tag_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        stmt = select(Tag).where(Tag.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_tag(self, tag_id: str, update_data: Dict[str, Any]) -> Optional[Tag]:
        """更新标签"""
        stmt = (
            update(Tag)
            .where(Tag.id == tag_id)
            .values(**update_data)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        if result.rowcount > 0:
            return await self.get_tag_by_id(tag_id)
        return None

    async def delete_tag(self, tag_id: str) -> bool:
        """删除标签"""
        stmt = delete(Tag).where(Tag.id == tag_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def delete_tag_by_name(self, name: str) -> bool:
        """根据名称删除标签"""
        stmt = delete(Tag).where(Tag.name == name)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_all_tags(
        self,
        skip: int = 0,
        limit: int = 20,
        query: Optional[str] = None,
        sort_by: str = "usage_count",
        sort_order: str = "desc"
    ) -> tuple[List[Tag], int]:
        """获取所有标签列表"""
        # 构建查询条件
        stmt = select(Tag)

        # 添加搜索条件
        if query:
            stmt = stmt.where(Tag.name.ilike(f"%{query}%") | Tag.description.ilike(f"%{query}%"))

        # 添加排序
        sort_column = getattr(Tag, sort_by, Tag.usage_count)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(sort_column)

        # 添加分页
        stmt = stmt.offset(skip).limit(limit)

        # 执行查询
        result = await self.db.execute(stmt)
        tags = result.scalars().all()

        # 获取总数
        count_stmt = select(count(Tag.id))
        if query:
            count_stmt = count_stmt.where(Tag.name.ilike(f"%{query}%") | Tag.description.ilike(f"%{query}%"))

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        return list(tags), total

    async def get_popular_tags(self, limit: int = 10) -> List[Tag]:
        """获取热门标签"""
        stmt = (
            select(Tag)
            .order_by(desc(Tag.usage_count))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_tag_usage(self, tag_names: List[str]) -> None:
        """增加标签使用次数"""
        if not tag_names:
            return

        # 批量更新标签使用次数
        for tag_name in tag_names:
            stmt = (
                update(Tag)
                .where(Tag.name == tag_name)
                .values(usage_count=Tag.usage_count + 1)
            )
            await self.db.execute(stmt)

        await self.db.commit()

    async def decrement_tag_usage(self, tag_names: List[str]) -> None:
        """减少标签使用次数"""
        if not tag_names:
            return

        # 批量更新标签使用次数（确保不小于0）
        for tag_name in tag_names:
            stmt = (
                update(Tag)
                .where(Tag.name == tag_name)
                .values(usage_count=func.greatest(Tag.usage_count - 1, 0))
            )
            await self.db.execute(stmt)

        await self.db.commit()

    async def get_tags_by_names(self, names: List[str]) -> List[Tag]:
        """根据名称列表获取标签"""
        if not names:
            return []

        stmt = select(Tag).where(Tag.name.in_(names))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_or_get_tags(self, names: List[str]) -> List[Tag]:
        """创建或获取标签"""
        if not names:
            return []

        tags = []
        for name in names:
            # 检查标签是否已存在
            existing_tag = await self.get_tag_by_name(name)
            if existing_tag:
                tags.append(existing_tag)
            else:
                # 创建新标签
                new_tag = await self.create_tag(name=name)
                tags.append(new_tag)

        return tags