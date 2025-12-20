"""
图片生成模块
"""

from .base import BaseImageProvider, ImageGenerationResult
from .factory import ImageProviderFactory
from .config import ImageGenerationConfig
from .providers.openai_compatible import OpenAICompatibleProvider
from .providers.gemini import GeminiProvider
from .providers.qwen import QwenProvider
from .providers.volcengine_ark import VolcengineArkProvider
from .providers.nano_banana import NanoBananaProvider

# 注册所有提供商
ImageProviderFactory.register_provider("openai_compatible", OpenAICompatibleProvider)
ImageProviderFactory.register_provider("gemini", GeminiProvider)
ImageProviderFactory.register_provider("qwen", QwenProvider)
ImageProviderFactory.register_provider("volcengine_ark", VolcengineArkProvider)
ImageProviderFactory.register_provider("nano_banana", NanoBananaProvider)

__all__ = [
    "BaseImageProvider",
    "ImageGenerationResult",
    "ImageProviderFactory",
    "ImageGenerationConfig",
    "OpenAICompatibleProvider",
    "GeminiProvider",
    "QwenProvider",
    "VolcengineArkProvider",
    "NanoBananaProvider"
]