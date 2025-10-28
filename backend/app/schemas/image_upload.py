"""
图片上传相关的Pydantic模型
用于数据验证和序列化
"""

from typing import Optional, List
from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """图片上传响应模型"""
    success: bool
    image_id: str
    image_url: str
    cos_key: str
    message: str


class PresignedUrlRequest(BaseModel):
    """预签名URL请求模型"""
    filename: str
    content_type: str


class PresignedUrlResponse(BaseModel):
    """预签名URL响应模型"""
    success: bool
    upload_url: str
    cos_key: str
    access_url: str
    expires_in: int
    message: str


class BatchUploadResult(BaseModel):
    """批量上传结果模型"""
    filename: str
    success: bool
    image_id: Optional[str] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    success: bool
    message: str
    total_files: int
    successful_uploads: int
    failed_uploads: int
    results: List[BatchUploadResult]
