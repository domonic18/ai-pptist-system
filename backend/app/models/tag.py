"""
标签数据模型
支持标签管理和统计
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime

from app.db.database import Base


class Tag(Base):
    """标签模型"""

    __tablename__ = "tags"

    # 基本字段
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # 统计字段
    usage_count = Column(Integer, default=0, nullable=False)

    # 时间戳
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name}, usage_count={self.usage_count})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }