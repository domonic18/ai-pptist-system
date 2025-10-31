"""
AI模型配置的Pydantic验证模型
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AIModelBase(BaseModel):
    """AI模型基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="模型显示名称")
    provider: str = Field(..., min_length=1, max_length=100, description="服务提供商")
    ai_model_name: str = Field(..., min_length=1, max_length=255, description="AI模型名称")
    base_url: Optional[str] = Field(None, max_length=512, description="API基础URL")
    api_key: Optional[str] = Field(None, description="API密钥（加密存储）")

    model_config = {
        "protected_namespaces": ()
    }


class AIModelCreate(AIModelBase):
    """创建AI模型请求模型"""
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认模型")
    max_tokens: Optional[str] = Field('8192', description="最大token数")
    context_window: Optional[str] = Field('16384', description="上下文窗口大小")
    model_settings: Optional[Dict[str, Any]] = Field(None, description="模型特定配置")
    # 能力配置
    supports_chat: bool = Field(True, description="是否支持聊天对话")
    supports_embeddings: bool = Field(False, description="是否支持嵌入")
    supports_vision: bool = Field(False, description="是否支持视觉")
    supports_tools: bool = Field(False, description="是否支持工具调用")
    supports_image_generation: bool = Field(False, description="是否支持图片生成")

    model_config = {
        "protected_namespaces": ()
    }

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """验证API密钥"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("API密钥不能为空字符串")
        return v

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """验证Base URL格式"""
        if v is not None:
            v = v.strip()
            if v and not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("Base URL必须以 http:// 或 https:// 开头")
        return v


class AIModelUpdate(BaseModel):
    """更新AI模型请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="模型显示名称")
    provider: Optional[str] = Field(None, min_length=1, max_length=100, description="服务提供商")
    ai_model_name: Optional[str] = Field(None, min_length=1, max_length=255, description="AI模型名称")
    base_url: Optional[str] = Field(None, max_length=512, description="API基础URL")
    api_key: Optional[str] = Field(None, description="API密钥（加密存储）")
    max_tokens: Optional[str] = Field(None, description="最大token数")
    context_window: Optional[str] = Field(None, description="上下文窗口大小")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否为默认模型")
    model_settings: Optional[Dict[str, Any]] = Field(None, description="模型特定配置")
    # 能力配置
    supports_chat: Optional[bool] = Field(None, description="是否支持聊天对话")
    supports_embeddings: Optional[bool] = Field(None, description="是否支持嵌入")
    supports_vision: Optional[bool] = Field(None, description="是否支持视觉")
    supports_tools: Optional[bool] = Field(None, description="是否支持工具调用")
    supports_image_generation: Optional[bool] = Field(None, description="是否支持图片生成")

    model_config = {
        "protected_namespaces": ()
    }

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """验证Base URL格式"""
        if v is not None:
            v = v.strip()
            if v and not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("Base URL必须以 http:// 或 https:// 开头")
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """验证API密钥"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("API密钥不能为空字符串")
        return v


class AIModelResponse(AIModelBase):
    """AI模型响应模型"""
    id: str
    max_tokens: Optional[str]
    context_window: Optional[str]
    is_enabled: bool
    is_default: bool
    model_settings: Optional[Dict[str, Any]] = None
    # 能力配置
    supports_chat: bool
    supports_embeddings: bool
    supports_vision: bool
    supports_tools: bool
    supports_image_generation: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class AIModelListResponse(BaseModel):
    """AI模型列表响应模型"""
    items: list[AIModelResponse]
    total: int


class AIModelSelection(BaseModel):
    """AI模型选择模型"""
    model_id: Optional[str] = Field(None, description="指定的模型ID")
    provider: Optional[str] = Field(None, description="服务提供商过滤")
    ai_model_name: Optional[str] = Field(None, description="AI模型名称过滤")

    model_config = {
        "protected_namespaces": ()
    }
