"""
AI模型数据访问层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc

from app.models.ai_model import AIModel
from .base import BaseRepository


class AIModelRepository(BaseRepository):
    """AI模型Repository"""

    @property
    def model(self):
        return AIModel

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_model_by_id(self, model_id: str) -> Optional[AIModel]:
        """根据ID获取模型"""
        return await self.get_by_id(model_id)

    async def list_models(
        self,
        enabled_only: bool = True,
        supports_image_generation: Optional[bool] = None
    ) -> List[AIModel]:
        """获取模型列表"""
        query = select(AIModel)
        if enabled_only:
            query = query.where(AIModel.is_enabled == True)
        if supports_image_generation is not None:
            query = query.where(AIModel.supports_image_generation == supports_image_generation)
        query = query.order_by(AIModel.is_default.desc(), AIModel.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_default_model(self) -> Optional[AIModel]:
        """获取默认模型"""
        query = select(AIModel).where(
            AIModel.is_default == True,
            AIModel.is_enabled == True
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_model_by_name(self, name: str) -> Optional[AIModel]:
        """根据名称获取模型"""
        query = select(AIModel).where(AIModel.name == name)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def create_model(self, **kwargs) -> AIModel:
        """创建新模型"""
        return await self.create(**kwargs)

    async def update_model(self, model_id: str, **kwargs) -> Optional[AIModel]:
        """更新模型"""
        return await self.update(model_id, **kwargs)

    async def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        query = delete(AIModel).where(AIModel.id == model_id)
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0