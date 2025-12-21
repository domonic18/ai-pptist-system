"""
OpenAI兼容Provider（支持DeepSeek、智谱AI等）
"""

from .chat import OpenAICompatibleChatProvider
from .vision import OpenAICompatibleVisionProvider

__all__ = [
    "OpenAICompatibleChatProvider",
    "OpenAICompatibleVisionProvider",
]

