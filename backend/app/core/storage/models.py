"""
存储服务数据模型
定义存储操作中使用的所有数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class UploadResult:
    """
    上传结果

    Attributes:
        key: 存储键
        url: 访问URL
        size: 文件大小（字节）
        mime_type: MIME类型
        bucket: 存储桶名称
        region: 区域
        etag: 文件ETag
        uploaded_at: 上传时间
    """
    key: str
    url: str
    size: int
    mime_type: str
    bucket: Optional[str] = None
    region: Optional[str] = None
    etag: Optional[str] = None
    uploaded_at: Optional[datetime] = None


@dataclass(frozen=True)
class DownloadResult:
    """
    下载结果

    Attributes:
        data: 文件数据
        size: 文件大小（字节）
        mime_type: MIME类型
        last_modified: 最后修改时间
        etag: 文件ETag
    """
    data: bytes
    size: int
    mime_type: str
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None


@dataclass(frozen=True)
class MetadataResult:
    """
    文件元数据

    Attributes:
        content_type: 内容类型
        content_length: 内容长度
        etag: 文件ETag
        last_modified: 最后修改时间
        metadata: 自定义元数据
    """
    content_type: str
    content_length: int
    etag: str
    last_modified: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class FileMetadata:
    """
    文件元信息（内部使用）

    Attributes:
        key: 存储键
        size: 文件大小
        content_type: 内容类型
        last_modified: 最后修改时间
        etag: 文件ETag
    """
    key: str
    size: int
    content_type: str
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None


__all__ = [
    'UploadResult',
    'DownloadResult',
    'MetadataResult',
    'FileMetadata',
]
