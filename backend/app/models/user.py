"""
用户数据模型
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB

from app.db.database import Base


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    # 基本字段
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='USER')
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)

    # SSO 认证相关字段
    auth_type = Column(String(20), default='password')  # password 或 saml
    saml_name_id = Column(String(255), nullable=True)
    saml_session_index = Column(String(255), nullable=True)
    saml_attributes = Column(JSONB, default=dict)
    last_sso_login_at = Column(TIMESTAMP, nullable=True)

    # 个人资料
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    preferences = Column(JSONB, default=dict)

    # 时间戳
    created_at = Column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    last_login_at = Column(TIMESTAMP, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def is_sso_user(self) -> bool:
        """是否为 SSO 用户"""
        return self.auth_type == 'saml'

    @property
    def is_password_user(self) -> bool:
        """是否为密码登录用户"""
        return self.auth_type == 'password'

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'auth_type': self.auth_type,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        }

    def to_safe_dict(self) -> Dict[str, Any]:
        """转换为安全字典格式（不包含敏感信息）"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'auth_type': self.auth_type,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        }
