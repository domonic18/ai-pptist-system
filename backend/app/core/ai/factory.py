"""
AI Provider工厂
"""

from typing import Dict, Type
from app.core.log_utils import get_logger
from .base import BaseAIProvider
from .models import ModelCapability
from .config import ModelConfig

logger = get_logger(__name__)


class AIProviderFactory:
    """AI Provider工厂类"""
    
    # Provider注册表: {capability: {provider_name: ProviderClass}}
    _providers: Dict[ModelCapability, Dict[str, Type[BaseAIProvider]]] = {}
    
    @classmethod
    def register(
        cls,
        capability: ModelCapability,
        provider_name: str,
        provider_class: Type[BaseAIProvider]
    ):
        """
        注册Provider
        
        Args:
            capability: 能力枚举
            provider_name: Provider名称
            provider_class: Provider类
        """
        if capability not in cls._providers:
            cls._providers[capability] = {}
        
        cls._providers[capability][provider_name] = provider_class
        logger.info(
            f"注册Provider: {capability.value}/{provider_name}",
            operation="register_provider",
            capability=capability.value,
            provider_name=provider_name
        )
    
    @classmethod
    def create(
        cls,
        model_config: ModelConfig,
        capability: ModelCapability
    ) -> BaseAIProvider:
        """
        创建Provider实例
        
        Args:
            model_config: 模型配置
            capability: 需要的能力
            
        Returns:
            Provider实例
            
        Raises:
            ValueError: 如果能力不支持或Provider未注册
        """
        # 从模型配置获取Provider名称
        provider_name = model_config.get_provider_for_capability(capability)
        if not provider_name:
            raise ValueError(
                f"模型 {model_config.model_id} 未配置 {capability.value} 的Provider"
            )
        
        # 检查能力是否支持
        if capability not in cls._providers:
            raise ValueError(f"不支持的能力: {capability.value}")
        
        # 检查Provider是否已注册
        if provider_name not in cls._providers[capability]:
            available = list(cls._providers[capability].keys())
            raise ValueError(
                f"未注册的Provider: {capability.value}/{provider_name}, "
                f"可用的Provider: {available}"
            )
        
        # 创建Provider实例
        provider_class = cls._providers[capability][provider_name]
        logger.info(
            f"创建Provider实例: {capability.value}/{provider_name}",
            operation="create_provider",
            capability=capability.value,
            provider_name=provider_name,
            model_id=model_config.model_id
        )
        
        return provider_class(model_config)
    
    @classmethod
    def get_available_providers(
        cls,
        capability: ModelCapability
    ) -> list[str]:
        """
        获取某种能力的所有可用Provider
        
        Args:
            capability: 能力枚举
            
        Returns:
            Provider名称列表
        """
        return list(cls._providers.get(capability, {}).keys())
    
    @classmethod
    def is_registered(
        cls,
        capability: ModelCapability,
        provider_name: str
    ) -> bool:
        """
        检查Provider是否已注册
        
        Args:
            capability: 能力枚举
            provider_name: Provider名称
            
        Returns:
            是否已注册
        """
        return (
            capability in cls._providers and
            provider_name in cls._providers[capability]
        )

