"""
图片相关的Pydantic模型
用于数据验证和序列化
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ImageBase(BaseModel):
    """图片基础模型"""
    prompt: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = False


class ImageCreate(ImageBase):
    """图片创建模型"""
    original_filename: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    image_url: Optional[str] = None
    cos_key: Optional[str] = None
    cos_bucket: Optional[str] = None
    cos_region: Optional[str] = None
    source_type: str = "uploaded"


class ImageUpdate(ImageBase):
    """图片更新模型"""
    pass


class ImageResponse(ImageBase):
    """图片响应模型"""
    id: str
    user_id: str
    image_url: Optional[str] = None
    source_type: str
    generation_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None
    storage_status: str
    cos_key: Optional[str] = None
    cos_bucket: Optional[str] = None
    cos_region: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class ImageListResponse(BaseModel):
    """图片列表响应模型"""
    images: List[ImageResponse]
    total: int
    skip: int
    limit: int


class ImageGenerationAndStoreRequest(BaseModel):
    """AI生成图片并存储请求模型"""
    prompt: str
    generation_model: str = "dall-e-3"
    width: int = 1024
    height: int = 1024
    quality: str = "standard"
    style: str = "vivid"
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = False


class ImageGenerationAndStoreResponse(BaseModel):
    """AI生成图片并存储响应模型"""
    success: bool
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    cos_key: Optional[str] = None
    message: str
    error: Optional[str] = None

