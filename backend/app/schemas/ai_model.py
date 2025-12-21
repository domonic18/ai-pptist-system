"""
AI模型配置的Pydantic验证模型（统一架构）
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class AIModelBase(BaseModel):
    """AI模型基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="模型显示名称")
    ai_model_name: str = Field(..., min_length=1, max_length=255, description="AI模型名称")
    base_url: Optional[str] = Field(None, max_length=512, description="API基础URL")
    api_key: Optional[str] = Field(None, description="API密钥")

    model_config = {
        "protected_namespaces": ()
    }


class AIModelCreate(AIModelBase):
    """创建AI模型请求模型"""
    # 统一架构：能力和Provider映射
    capabilities: List[str] = Field(..., min_length=1, description="模型支持的能力列表")
    provider_mapping: Dict[str, str] = Field(..., description="能力到Provider的映射")
    
    # 模型配置
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="模型参数配置")
    max_tokens: Optional[int] = Field(8192, description="最大token数")
    context_window: Optional[int] = Field(16384, description="上下文窗口大小")
    
    # 状态管理
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认模型")

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

    @field_validator('capabilities')
    @classmethod
    def validate_capabilities(cls, v):
        """验证能力列表"""
        if not v or len(v) == 0:
            raise ValueError("至少需要指定一个能力")
        
        valid_capabilities = {'chat', 'vision', 'image_gen', 'video_gen', 'embeddings', 'tools', 'code'}
        for cap in v:
            if cap not in valid_capabilities:
                raise ValueError(f"无效的能力: {cap}，有效的能力包括: {', '.join(valid_capabilities)}")
        
        return v

    @field_validator('provider_mapping')
    @classmethod
    def validate_provider_mapping(cls, v, info):
        """验证Provider映射"""
        # 确保所有能力都有对应的Provider
        if 'capabilities' in info.data:
            capabilities = info.data['capabilities']
            for cap in capabilities:
                if cap not in v:
                    raise ValueError(f"能力 '{cap}' 缺少Provider映射")
        
        return v


class AIModelUpdate(BaseModel):
    """更新AI模型请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="模型显示名称")
    ai_model_name: Optional[str] = Field(None, min_length=1, max_length=255, description="AI模型名称")
    base_url: Optional[str] = Field(None, max_length=512, description="API基础URL")
    api_key: Optional[str] = Field(None, description="API密钥")
    
    # 统一架构：能力和Provider映射
    capabilities: Optional[List[str]] = Field(None, description="模型支持的能力列表")
    provider_mapping: Optional[Dict[str, str]] = Field(None, description="能力到Provider的映射")
    
    # 模型配置
    parameters: Optional[Dict[str, Any]] = Field(None, description="模型参数配置")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    context_window: Optional[int] = Field(None, description="上下文窗口大小")
    
    # 状态管理
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否为默认模型")

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

    @field_validator('capabilities')
    @classmethod
    def validate_capabilities(cls, v):
        """验证能力列表"""
        if v is not None:
            if len(v) == 0:
                raise ValueError("至少需要指定一个能力")
            
            valid_capabilities = {'chat', 'vision', 'image_gen', 'video_gen', 'embeddings', 'tools', 'code'}
            for cap in v:
                if cap not in valid_capabilities:
                    raise ValueError(f"无效的能力: {cap}")
        
        return v


class AIModelResponse(AIModelBase):
    """AI模型响应模型"""
    id: str
    
    # 统一架构：能力和Provider映射
    capabilities: List[str]
    provider_mapping: Dict[str, str]
    
    # 模型配置
    parameters: Optional[Dict[str, Any]] = {}
    max_tokens: Optional[int]
    context_window: Optional[int]
    
    # 状态管理
    is_enabled: bool
    is_default: bool
    
    # 时间戳
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
    capability: Optional[str] = Field(None, description="能力类型过滤")

    model_config = {
        "protected_namespaces": ()
    }
