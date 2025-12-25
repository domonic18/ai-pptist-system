"""
存储服务异常定义
定义存储模块中使用的所有异常类型
"""

from typing import Any, Dict, Optional


class StorageError(Exception):
    """
    存储操作基础异常

    所有存储相关异常的基类。

    Attributes:
        message: 错误消息
        code: 错误码
        details: 错误详情
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class ConfigurationError(StorageError):
    """存储配置错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="CONFIG_ERROR", details=details)


class ClientError(StorageError):
    """存储客户端错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="CLIENT_ERROR", details=details)


class UploadError(StorageError):
    """文件上传错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="UPLOAD_ERROR", details=details)


class DownloadError(StorageError):
    """文件下载错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="DOWNLOAD_ERROR", details=details)


class DeleteError(StorageError):
    """文件删除错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="DELETE_ERROR", details=details)


class URLError(StorageError):
    """预签名URL生成错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="URL_ERROR", details=details)


class MetadataError(StorageError):
    """元数据获取错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="METADATA_ERROR", details=details)


class HTTPError(StorageError):
    """HTTP请求错误"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, code="HTTP_ERROR", details=details)
        self.status_code = status_code


class NetworkError(StorageError):
    """网络请求错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="NETWORK_ERROR", details=details)


__all__ = [
    'StorageError',
    'ConfigurationError',
    'ClientError',
    'UploadError',
    'DownloadError',
    'DeleteError',
    'URLError',
    'MetadataError',
    'HTTPError',
    'NetworkError',
]
