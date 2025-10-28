"""
AI模型配置数据模型
支持多模型配置和管理
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base


class AIModel(Base):
    """AI模型配置模型"""

    __tablename__ = "ai_models"

    # 基本字段
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="模型显示名称")
    provider = Column(String(100), nullable=False, comment="服务提供商")
    model_name = Column(String(255), nullable=False, comment="模型名称")

    # API配置
    base_url = Column(String(512), nullable=True, comment="API基础URL")
    api_key = Column(Text, nullable=False, comment="API密钥")

    # 模型配置
    model_settings = Column(JSONB, nullable=True, comment="模型特定配置")

    # 状态管理
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否为默认模型")

    # 能力配置
    supports_chat = Column(Boolean, default=True, comment="是否支持聊天对话")
    supports_embeddings = Column(Boolean, default=False, comment="是否支持嵌入")
    supports_vision = Column(Boolean, default=False, comment="是否支持视觉")
    supports_tools = Column(Boolean, default=False, comment="是否支持工具调用")
    supports_image_generation = Column(Boolean, default=False, comment="是否支持图片生成")

    # 限制配置
    max_tokens = Column(String(20), default="8192", comment="最大token数")
    context_window = Column(String(20), default="16384", comment="上下文窗口大小")

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
        return f"<AIModel(id={self.id}, name={self.name}, provider={self.provider})>"

    @property
    def is_openai_compatible(self) -> bool:
        """是否为OpenAI兼容的API"""
        return self.provider.lower() in ['openai', 'azure', 'anthropic', 'cohere']

    @property
    def api_endpoint(self) -> Optional[str]:
        """获取完整的API端点"""
        if not self.base_url:
            return None

        if self.provider.lower() == 'openai':
            return f"{self.base_url}/v1/chat/completions"
        elif self.provider.lower() == 'azure':
            return f"{self.base_url}/openai/deployments/{self.model_name}/chat/completions"
        else:
            return f"{self.base_url}/chat/completions"