"""
AI Provider统一抽象基类
"""

from abc import ABC, abstractmethod
from typing import Set, TYPE_CHECKING

from .models import ModelCapability

if TYPE_CHECKING:
    from app.core.ai.config import ModelConfig


class BaseAIProvider(ABC):
    """所有AI Provider的统一抽象基类"""
    
    def __init__(self, model_config: 'ModelConfig'):
        """
        初始化Provider
        
        Args:
            model_config: 模型配置对象
        """
        self.model_config = model_config
        self._initialize()
    
    def _initialize(self):
        """Provider初始化逻辑（子类可以覆盖）"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Set[ModelCapability]:
        """
        获取Provider支持的能力
        
        Returns:
            能力集合
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取Provider名称
        
        Returns:
            Provider名称（如 "openai", "gemini"）
        """
        pass
    
    async def close(self):
        """关闭Provider，释放资源"""
        pass
    
    def supports_capability(self, capability: ModelCapability) -> bool:
        """
        检查是否支持某种能力
        
        Args:
            capability: 能力枚举
            
        Returns:
            是否支持该能力
        """
        return capability in self.get_capabilities()

