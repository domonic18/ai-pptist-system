"""
SAML认证异常定义
定义SAML SSO认证模块中使用的所有异常类型
"""

from typing import Any, Dict, Optional


class SAMLError(Exception):
    """
    SAML认证基础异常

    所有SAML相关异常的基类。

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


class SAMLValidationError(SAMLError):
    """SAML验证失败"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_VALIDATION_ERROR", details=details)


class SAMLUserCreationError(SAMLError):
    """用户创建失败"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_USER_CREATION_ERROR", details=details)


class SAMLMetadataError(SAMLError):
    """元数据生成失败"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_METADATA_ERROR", details=details)


class SAMLConfigurationError(SAMLError):
    """SAML配置错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_CONFIG_ERROR", details=details)


class SAMLResponseError(SAMLError):
    """SAML响应处理错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_RESPONSE_ERROR", details=details)


class SAMLErrorRequestError(SAMLError):
    """SAML请求处理错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="SAML_REQUEST_ERROR", details=details)


__all__ = [
    'SAMLError',
    'SAMLValidationError',
    'SAMLUserCreationError',
    'SAMLMetadataError',
    'SAMLConfigurationError',
    'SAMLResponseError',
    'SAMLErrorRequestError',
]
