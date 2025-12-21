"""
图片生成提供商工厂
负责创建和管理图片生成提供商实例
"""

from typing import Dict, Type, Optional, List
from app.core.log_utils import get_logger
from .base import BaseImageProvider

logger = get_logger(__name__)


class ImageProviderFactory:
    """图片生成提供商工厂"""

    _providers: Dict[str, Type[BaseImageProvider]] = {}

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[BaseImageProvider]):
        """
        注册提供商

        Args:
            provider_name: 提供商名称
            provider_class: 提供商类
        """
        if provider_name in cls._providers:
            logger.warning("提供商已存在，将被覆盖", extra={"provider_name": provider_name})

        cls._providers[provider_name] = provider_class
        logger.info("注册图片生成提供商", extra={"provider_name": provider_name})

    @classmethod
    def create_provider(cls, model_config) -> BaseImageProvider:
        """
        创建提供商实例

        Args:
            model_config: 模型配置对象

        Returns:
            BaseImageProvider: 提供商实例

        Raises:
            ValueError: 如果提供商类型不支持
        """
        provider_name = getattr(model_config, 'provider', 'openai')

        if provider_name not in cls._providers:
            raise ValueError(f"不支持的提供商类型: {provider_name}")

        provider_class = cls._providers[provider_name]
        return provider_class(model_config)

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[Type[BaseImageProvider]]:
        """
        根据模型名称获取提供商类

        Args:
            model_name: 模型名称

        Returns:
            Optional[Type[BaseImageProvider]]: 提供商类，如果找不到则返回None
        """
        for provider_class in cls._providers.values():
            if provider_class.supports_model(model_name):
                return provider_class
        return None

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[BaseImageProvider]]:
        """
        获取所有可用的提供商

        Returns:
            Dict[str, Type[BaseImageProvider]]: 提供商名称到类的映射
        """
        return cls._providers.copy()

    @classmethod
    def is_provider_supported(cls, provider_name: str) -> bool:
        """
        检查是否支持指定的提供商

        Args:
            provider_name: 提供商名称

        Returns:
            bool: 是否支持该提供商
        """
        return provider_name in cls._providers

    @classmethod
    def get_supported_models(cls) -> Dict[str, List[str]]:
        """
        获取所有提供商支持的模型列表

        Returns:
            Dict[str, List[str]]: 提供商名称到支持的模型列表的映射
        """
        result = {}
        for provider_name, provider_class in cls._providers.items():
            try:
                # 使用默认配置创建实例
                dummy_config = type('DummyConfig', (), {'provider': provider_name})()
                provider_instance = provider_class(dummy_config)
                result[provider_name] = provider_instance.get_supported_models()
            except Exception as e:
                logger.warning("获取提供商支持的模型失败", extra={
                    "provider_name": provider_name,
                    "error": str(e)
                })
                result[provider_name] = []

        return result