"""
图片生成提供商注册
管理图片生成提供商的注册和查询
"""

from typing import Type

from app.core.log_utils import get_logger
from .base import BaseImageProvider
from .factory import ImageProviderFactory

logger = get_logger(__name__)


def register_all_providers():
    """注册所有图片生成提供商
    
    这个函数应该在应用启动时被调用一次
    """
    from .providers.openai_compatible import OpenAICompatibleProvider
    from .providers.gemini import GeminiProvider
    from .providers.qwen import QwenProvider
    from .providers.volcengine_ark import VolcengineArkProvider
    from .providers.nano_banana import NanoBananaProvider
    
    providers = [
        ("openai_compatible", OpenAICompatibleProvider),
        ("gemini", GeminiProvider),
        ("qwen", QwenProvider),
        ("volcengine_ark", VolcengineArkProvider),
        ("nano_banana", NanoBananaProvider),
    ]
    
    for provider_name, provider_class in providers:
        ImageProviderFactory.register_provider(provider_name, provider_class)
    
    logger.info(
        "已注册所有图片生成提供商",
        operation="register_all_providers",
        provider_count=len(providers)
    )


def register_provider(provider_name: str, provider_class: Type[BaseImageProvider]):
    """注册单个图片生成提供商
    
    Args:
        provider_name: 提供商名称
        provider_class: 提供商类
    """
    ImageProviderFactory.register_provider(provider_name, provider_class)

