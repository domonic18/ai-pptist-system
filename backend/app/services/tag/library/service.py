"""
标签库服务
处理标签库相关的核心业务逻辑
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tag import TagRepository
from app.schemas.tag_library import TagCreate, TagSearchParams
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class TagLibraryService:
    """标签库服务 - 处理标签库相关的核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_repo = TagRepository(db)

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