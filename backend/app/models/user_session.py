"""
用户会话数据模型
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import Column, String, Text, Index
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db.database import Base


class UserSession(Base):
    """用户会话模型 - 存储 JWT Token 会话信息"""

    __tablename__ = "user_sessions"

    # 主键
    id = Column(String(36), primary_key=True)

    # 用户关联（移除 index=True，避免与 __table_args__ 中的索引重复）
    user_id = Column(String(36), nullable=False)

    # Token 标识
    # 移除 token_jti 的 index=True（unique 约束会自动创建索引）
    token_jti = Column(String(255), unique=True, nullable=False)

    # refresh_token_jti：移除 index，保留 unique 约束
    refresh_token_jti = Column(String(255), unique=True, nullable=True)

    # 会话信息
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # 过期时间
    expires_at = Column(TIMESTAMP, nullable=False)
    refresh_expires_at = Column(TIMESTAMP, nullable=True)

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
    # revoked_at 不需要索引，因为查询通常通过 token_jti 进行
    revoked_at = Column(TIMESTAMP, nullable=True)

    # 索引定义
    # 注意：PostgreSQL 复合索引可以用于前导列的单列查询，因此不需要单独创建 user_id 索引
    __table_args__ = (
        # 查询活跃会话：user_id + revoked_at IS NULL + expires_at > NOW()
        # 此索引也可用于仅基于 user_id 的查询（前导列优化）
        Index('ix_user_sessions_active', 'user_id', 'revoked_at', 'expires_at'),
    )

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, token_jti={self.token_jti})>"

    @property
    def is_active(self) -> bool:
        """会话是否活跃"""
        if self.revoked_at is not None:
            return False
        # 确保 expires_at 是 naive datetime 进行比较
        expires_at_naive = self.expires_at.replace(tzinfo=None) if self.expires_at and self.expires_at.tzinfo else self.expires_at
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if expires_at_naive < now:
            return False
        return True

    @property
    def is_revoked(self) -> bool:
        """会话是否已撤销"""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """会话是否已过期"""
        # 确保 expires_at 是 naive datetime 进行比较
        expires_at_naive = self.expires_at.replace(tzinfo=None) if self.expires_at and self.expires_at.tzinfo else self.expires_at
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return expires_at_naive < now

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token_jti': self.token_jti,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'refresh_expires_at': self.refresh_expires_at.isoformat() if self.refresh_expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active,
        }
