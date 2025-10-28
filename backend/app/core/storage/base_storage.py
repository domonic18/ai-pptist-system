"""
存储抽象基类
定义统一的存储接口，支持多种存储后端
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadResult:
    """上传结果"""
    key: str
    url: str
    size: int
    mime_type: str
    bucket: Optional[str] = None
    region: Optional[str] = None
    etag: Optional[str] = None
    uploaded_at: Optional[datetime] = None


@dataclass
class DownloadResult:
    """下载结果"""
    data: bytes
    size: int
    mime_type: str
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None


class BaseStorage(ABC):
    """存储抽象基类"""

    @abstractmethod
    async def upload(
        self,
        data: bytes,
        key: str,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        上传文件

        Args:
            data: 文件数据
            key: 存储键
            mime_type: MIME类型
            metadata: 可选的元数据

        Returns:
            UploadResult: 上传结果

        Raises:
            StorageError: 上传失败时抛出
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> DownloadResult:
        """
        下载文件

        Args:
            key: 存储键

        Returns:
            DownloadResult: 下载结果

        Raises:
            StorageError: 下载失败时抛出
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        删除文件

        Args:
            key: 存储键

        Returns:
            bool: 删除是否成功

        Raises:
            StorageError: 删除失败时抛出
        """
        pass

    @abstractmethod
    async def generate_url(
        self,
        key: str,
        expires: int = 3600,
        operation: str = "get"
    ) -> str:
        """
        生成访问URL

        Args:
            key: 存储键
            expires: 过期时间（秒）
            operation: 操作类型（get/put等）

        Returns:
            str: 访问URL

        Raises:
            StorageError: 生成URL失败时抛出
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 存储键

        Returns:
            bool: 文件是否存在
        """
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            key: 存储键

        Returns:
            Dict[str, Any]: 文件元数据

        Raises:
            StorageError: 获取元数据失败时抛出
        """
        pass


class StorageError(Exception):
    """存储操作异常"""

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message