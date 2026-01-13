"""
SAML SSO 认证相关 Schema
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.auth import UserResponse


# ==================== 请求 Schema ====================

class SSOInitRequest(BaseModel):
    """SSO初始化请求"""
    return_to: Optional[str] = Field(None, description="登录成功后重定向URL")

    class Config:
        json_schema_extra = {
            "example": {
                "return_to": "http://localhost:3005/dashboard"
            }
        }


class SSOLogoutRequest(BaseModel):
    """SLO请求"""
    saml_name_id: Optional[str] = Field(None, description="SAML NameID")
    saml_session_index: Optional[str] = Field(None, description="SAML SessionIndex")

    class Config:
        json_schema_extra = {
            "example": {
                "saml_name_id": "user@example.com",
                "saml_session_index": "session-index-123"
            }
        }


# ==================== 响应 Schema ====================

class SSOResponse(BaseModel):
    """SSO登录响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_at: datetime = Field(..., description="访问令牌过期时间")
    refresh_expires_at: datetime = Field(..., description="刷新令牌过期时间")
    user: UserResponse = Field(..., description="用户信息")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-13T10:30:00Z",
                "refresh_expires_at": "2024-02-12T10:30:00Z",
                "user": {
                    "id": "user-id-123",
                    "email": "user@example.com",
                    "name": "张三",
                    "role": "USER",
                    "is_active": True,
                    "is_superuser": False,
                    "auth_type": "saml"
                }
            }
        }


class SSOMetadataResponse(BaseModel):
    """SP元数据响应"""
    metadata: str = Field(..., description="SP元数据XML字符串")

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": "<?xml version=\"1.0\"?>..."
            }
        }
