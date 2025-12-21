"""
AI模型配置管理
"""

from typing import Optional, Dict, Any, List
from .models import ModelCapability


class ModelConfig:
    """AI模型配置类"""
    
    def __init__(
        self,
        model_id: str,
        model_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        provider_mapping: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        context_window: Optional[int] = None
    ):
        """
        初始化模型配置
        
        Args:
            model_id: 模型ID
            model_name: 模型名称（如 "gpt-4-turbo"）
            api_key: API密钥
            base_url: API基础URL
            capabilities: 支持的能力列表
            provider_mapping: Provider映射（如 {"chat": "openai", "image_gen": "dalle"}）
            parameters: 其他参数
            max_tokens: 最大Token数
            context_window: 上下文窗口大小
        """
        self.model_id = model_id
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.capabilities = capabilities or []
        self.provider_mapping = provider_mapping or {}
        self.parameters = parameters or {}
        self.max_tokens = max_tokens
        self.context_window = context_window
    
    def get_provider_for_capability(self, capability: ModelCapability) -> Optional[str]:
        """
        获取某个能力对应的Provider名称
        
        Args:
            capability: 能力枚举
            
        Returns:
            Provider名称，如果未配置则返回None
        """
        return self.provider_mapping.get(capability.value)
    
    def supports_capability(self, capability: ModelCapability) -> bool:
        """
        检查是否支持某种能力
        
        Args:
            capability: 能力枚举
            
        Returns:
            是否支持该能力
        """
        return capability.value in self.capabilities
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """
        从字典创建配置对象
        
        Args:
            data: 配置数据字典
            
        Returns:
            ModelConfig实例
        """
        return cls(
            model_id=data.get('id', ''),
            model_name=data.get('ai_model_name', ''),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url'),
            capabilities=data.get('capabilities', []),
            provider_mapping=data.get('provider_mapping', {}),
            parameters=data.get('parameters', {}),
            max_tokens=data.get('max_tokens'),
            context_window=data.get('context_window')
        )

