"""
图片生成模块
提供统一的图片生成接口和多种提供商实现
"""

# 核心类
from .base import BaseImageProvider
from .models import ImageGenerationResult
from .factory import ImageProviderFactory
from .config import ImageGenerationConfig

# 注册功能
from .registry import register_all_providers, register_provider

# 提供商类（用于类型提示和直接导入）
from .providers.openai_compatible import OpenAICompatibleProvider
from .providers.gemini import GeminiProvider
from .providers.qwen import QwenProvider
from .providers.volcengine_ark import VolcengineArkProvider
from .providers.nano_banana import NanoBananaProvider

__all__ = [
    # 核心类
    "BaseImageProvider",
    "ImageGenerationResult",
    "ImageProviderFactory",
    "ImageGenerationConfig",
    # 注册功能
    "register_all_providers",
    "register_provider",
    # 提供商类
    "OpenAICompatibleProvider",
    "GeminiProvider",
    "QwenProvider",
    "VolcengineArkProvider",
    "NanoBananaProvider",
]