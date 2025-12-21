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
    
    @classmethod
    def create_provider(
        cls,
        capability: ModelCapability,
        provider_name: str,
        model_config: any
    ) -> BaseAIProvider:
        """
        创建Provider实例（简化接口，用于服务层调用）
        
        这是一个便捷方法，接受任意配置对象/字典，内部转换为ModelConfig
        
        Args:
            capability: 需要的能力
            provider_name: Provider名称
            model_config: 模型配置（可以是字典或对象）
            
        Returns:
            Provider实例
            
        Raises:
            ValueError: 如果能力不支持或Provider未注册
        """
        from .config import ModelConfig
        
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
        
        # 转换配置对象
        if isinstance(model_config, ModelConfig):
            # 已经是ModelConfig对象，直接使用
            config = model_config
        elif isinstance(model_config, dict):
            # 字典格式，使用from_dict转换
            logger.debug(
                "从字典创建ModelConfig",
                operation="create_provider_from_dict",
                config_keys=list(model_config.keys()),
                has_api_key='api_key' in model_config,
                api_key_length=len(model_config.get('api_key', '')) if 'api_key' in model_config else 0
            )
            config = ModelConfig.from_dict(model_config)
            logger.debug(
                "ModelConfig创建完成",
                operation="model_config_created",
                model_id=config.model_id,
                model_name=config.model_name,
                base_url=config.base_url,
                api_key_length=len(config.api_key) if config.api_key else 0
            )
        else:
            # 其他对象，尝试获取属性
            config = ModelConfig(
                model_id=getattr(model_config, 'id', getattr(model_config, 'model_id', 'unknown')),
                model_name=getattr(model_config, 'ai_model_name', getattr(model_config, 'name', 'unknown')),
                api_key=getattr(model_config, 'api_key', ''),
                base_url=getattr(model_config, 'base_url', None),
                capabilities=getattr(model_config, 'capabilities', [capability.value]),
                provider_mapping=getattr(model_config, 'provider_mapping', {capability.value: provider_name}),
                parameters=getattr(model_config, 'parameters', {}),
                max_tokens=getattr(model_config, 'max_tokens', None),
                context_window=getattr(model_config, 'context_window', None)
            )
        
        # 创建Provider实例
        provider_class = cls._providers[capability][provider_name]
        logger.info(
            f"创建Provider实例: {capability.value}/{provider_name}",
            operation="create_provider",
            capability=capability.value,
            provider_name=provider_name,
            model_id=config.model_id
        )
        
        return provider_class(config)

