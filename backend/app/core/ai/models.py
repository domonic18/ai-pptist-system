"""
AI模型交互的数据模型
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class ModelCapability(str, Enum):
    """模型能力枚举"""
    CHAT = "chat"
    VISION = "vision"
    IMAGE_GEN = "image_gen"
    VIDEO_GEN = "video_gen"
    EMBEDDINGS = "embeddings"
    TOOLS = "tools"
    CODE = "code"


@dataclass
class ImageGenerationResult:
    """图片生成结果"""
    success: bool
    image_url: Optional[str] = None
    image: Optional[Any] = None  # PIL Image 对象
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    success: bool
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

