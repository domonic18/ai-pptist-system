"""
图片生成数据模型
定义图片生成相关的数据结构
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ImageGenerationResult:
    """图片生成结果
    
    Attributes:
        success: 是否生成成功
        image_url: 生成的图片URL（成功时）
        error_message: 错误消息（失败时）
        metadata: 额外的元数据信息
    """
    success: bool
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

