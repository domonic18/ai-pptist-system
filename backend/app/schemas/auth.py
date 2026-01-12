"""
认证相关 Schema
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime


# ==================== 请求 Schema ====================

class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, description="用户密码")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123"
            }
        }


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    name: str = Field(..., min_length=2, max_length=100, description="用户姓名")
    password: str = Field(..., min_length=8, description="用户密码（至少8位）")
    confirm_password: str = Field(..., min_length=8, description="确认密码")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """验证两次密码输入是否一致"""
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "张三",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        }


class TokenRefreshRequest(BaseModel):
    """Token 刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ==================== 响应 Schema ====================

class UserResponse(BaseModel):
    """用户信息响应"""
    id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    name: str = Field(..., description="用户姓名")
    role: str = Field(..., description="用户角色")
    is_active: bool = Field(..., description="账户是否激活")
    is_superuser: bool = Field(..., description="是否为超级用户")
    auth_type: str = Field(..., description="认证类型: password 或 saml")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="个人简介")
    created_at: Optional[datetime] = Field(None, description="注册时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应"""
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
                    "auth_type": "password"
                }
            }
        }


class RegisterResponse(BaseModel):
    """注册响应"""
    user: UserResponse = Field(..., description="用户信息")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_at: datetime = Field(..., description="访问令牌过期时间")
    refresh_expires_at: datetime = Field(..., description="刷新令牌过期时间")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "user-id-123",
                    "email": "user@example.com",
                    "name": "张三",
                    "role": "USER",
                    "is_active": True,
                    "is_superuser": False,
                    "auth_type": "password"
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-13T10:30:00Z",
                "refresh_expires_at": "2024-02-12T10:30:00Z"
            }
        }


class TokenRefreshResponse(BaseModel):
    """Token 刷新响应

    注意：每次刷新 token 时，refresh_token 也会更新（为了避免数据库唯一约束冲突）
    客户端需要保存新的 refresh_token
    """
    access_token: str = Field(..., description="新的访问令牌")
    refresh_token: str = Field(..., description="新的刷新令牌（每次刷新都会更新）")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_at: datetime = Field(..., description="访问令牌过期时间")
    refresh_expires_at: datetime = Field(..., description="刷新令牌过期时间")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-13T11:30:00Z",
                "refresh_expires_at": "2024-02-12T10:30:00Z"
            }
        }


class LogoutResponse(BaseModel):
    """登出响应"""
    message: str = Field(default="登出成功", description="响应消息")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "登出成功"
            }
        }


# ==================== 内部使用 Schema ====================

class TokenPayload(BaseModel):
    """Token 载荷"""
    sub: str = Field(..., description="用户ID")
    jti: str = Field(..., description="JWT ID")
    type: str = Field(..., description="Token类型: access 或 refresh")
    exp: datetime = Field(..., description="过期时间")
    iat: datetime = Field(..., description="签发时间")


class SessionInfo(BaseModel):
    """会话信息"""
    id: str = Field(..., description="会话ID")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: datetime = Field(..., description="过期时间")
    is_current: bool = Field(default=False, description="是否为当前会话")


class SessionsListResponse(BaseModel):
    """会话列表响应"""
    sessions: list[SessionInfo] = Field(..., description="会话列表")
    total: int = Field(..., description="总会话数")

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "id": "session-id-123",
                        "ip_address": "192.168.1.1",
                        "user_agent": "Mozilla/5.0...",
                        "created_at": "2024-01-13T10:00:00Z",
                        "expires_at": "2024-01-13T11:00:00Z",
                        "is_current": True
                    }
                ],
                "total": 1
            }
        }
