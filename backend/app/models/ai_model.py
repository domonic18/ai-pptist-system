"""
AI模型配置数据模型（统一架构）
支持多种AI能力和多Provider配置
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ARRAY
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base


class AIModel(Base):
    """AI模型配置模型（统一架构）"""

    __tablename__ = "ai_models"

    # 基本字段
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="模型显示名称")
    ai_model_name = Column(String(255), nullable=False, comment="AI模型名称")

    # API配置
    base_url = Column(String(512), nullable=True, comment="API基础URL")
    api_key = Column(Text, nullable=False, comment="API密钥")

    # 统一架构：能力和Provider映射
    capabilities = Column(ARRAY(Text), nullable=False, default=[], comment="模型支持的能力列表")
    provider_mapping = Column(JSONB, nullable=False, default={}, comment="能力到Provider的映射")

    # 模型配置
    parameters = Column(JSONB, nullable=True, default={}, comment="模型参数配置")
    max_tokens = Column(Integer, default=8192, comment="最大token数")
    context_window = Column(Integer, default=16384, comment="上下文窗口大小")

    # 状态管理
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否为默认模型")

    # 时间戳
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<AIModel(id={self.id}, name={self.name}, capabilities={self.capabilities})>"

    def has_capability(self, capability: str) -> bool:
        """检查模型是否支持指定能力"""
        return capability in (self.capabilities or [])

    def get_provider_for_capability(self, capability: str) -> Optional[str]:
        """获取指定能力的Provider"""
        if not self.has_capability(capability):
            return None
        return self.provider_mapping.get(capability) if self.provider_mapping else None

    @property
    def is_chat_model(self) -> bool:
        """是否为对话模型"""
        return self.has_capability('chat')

    @property
    def is_vision_model(self) -> bool:
        """是否为多模态模型"""
        return self.has_capability('vision')

    @property
    def is_image_generation_model(self) -> bool:
        """是否为图片生成模型"""
        return self.has_capability('image_gen')

    @property
    def is_video_generation_model(self) -> bool:
        """是否为视频生成模型"""
        return self.has_capability('video_gen')