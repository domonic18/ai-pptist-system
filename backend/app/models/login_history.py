"""
登录历史数据模型
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db.database import Base


class LoginHistory(Base):
    """登录历史模型 - 记录用户登录尝试"""

    __tablename__ = "login_history"

    # 主键（不需要 index=True，主键已自动创建索引）
    id = Column(String(36), primary_key=True)

    # 用户关联（可为空，用于记录未成功的登录尝试）
    user_id = Column(String(36), nullable=True, index=True)

    # 认证信息（移除 index=True，低基数字段索引效率低）
    auth_type = Column(String(20), nullable=False)  # password 或 saml
    login_status = Column(String(20), nullable=False)  # success 或 failed
    failure_reason = Column(String(255), nullable=True)

    # 请求信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # SSO 相关信息
    saml_name_id = Column(String(255), nullable=True, index=True)

    # 时间戳（保留索引，用于排序查询）
    created_at = Column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        return f"<LoginHistory(id={self.id}, user_id={self.user_id}, status={self.login_status})>"

    @property
    def is_success(self) -> bool:
        """登录是否成功"""
        return self.login_status == 'success'

    @property
    def is_failed(self) -> bool:
        """登录是否失败"""
        return self.login_status == 'failed'

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'auth_type': self.auth_type,
            'login_status': self.login_status,
            'failure_reason': self.failure_reason,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'saml_name_id': self.saml_name_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
