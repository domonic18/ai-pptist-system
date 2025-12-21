"""
AI能力基类定义
"""

from .chat import BaseChatProvider
from .vision import BaseVisionProvider
from .image_gen import BaseImageGenProvider
from .video_gen import BaseVideoGenProvider

__all__ = [
    "BaseChatProvider",
    "BaseVisionProvider",
    "BaseImageGenProvider",
    "BaseVideoGenProvider",
]

