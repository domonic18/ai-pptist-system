"""
AI模型数据访问层（统一架构）
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.models.ai_model import AIModel
from .base import BaseRepository


class AIModelRepository(BaseRepository):
    """AI模型Repository（统一架构）"""

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
        capability: Optional[str] = None
    ) -> List[AIModel]:
        """获取模型列表
        
        Args:
            enabled_only: 是否只返回启用的模型
            capability: 按能力过滤（如 'chat', 'image_gen'等）
        """
        query = select(AIModel)
        
        conditions = []
        if enabled_only:
            conditions.append(AIModel.is_enabled == True)
        if capability:
            # 使用 ANY 操作符查询数组字段
            conditions.append(AIModel.capabilities.contains([capability]))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AIModel.is_default.desc(), AIModel.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_default_model(self, capability: Optional[str] = None) -> Optional[AIModel]:
        """获取默认模型
        
        Args:
            capability: 如果指定，返回支持该能力的默认模型
        """
        conditions = [
            AIModel.is_default == True,
            AIModel.is_enabled == True
        ]
        
        if capability:
            conditions.append(AIModel.capabilities.contains([capability]))
        
        query = select(AIModel).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_model_by_name(self, name: str) -> Optional[AIModel]:
        """根据名称获取模型"""
        query = select(AIModel).where(AIModel.name == name)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_models_by_capability(
        self, 
        capability: str,
        enabled_only: bool = True
    ) -> List[AIModel]:
        """根据能力获取模型列表"""
        conditions = [AIModel.capabilities.contains([capability])]
        
        if enabled_only:
            conditions.append(AIModel.is_enabled == True)
        
        query = select(AIModel).where(and_(*conditions))
        query = query.order_by(AIModel.is_default.desc(), AIModel.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

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