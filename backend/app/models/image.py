"""
图片数据模型
统一图片模型，支持生成和上传的图片
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import Column, String, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.db.database import Base


class Image(Base):
    """统一的图片模型 - 支持生成和上传的图片"""

    __tablename__ = "images"

    # 基本字段
    id = Column(String(30), primary_key=True, index=True)
    user_id = Column(String(30), nullable=False, index=True)

    # 图片内容字段
    prompt = Column(Text, nullable=True)  # 对于用户上传的图片，此字段可能为空
    image_url = Column(Text, nullable=True)  # 允许为空，对于上传图片可能暂时没有URL

    # COS存储相关字段
    cos_key = Column(Text, nullable=True)  # COS对象键
    cos_bucket = Column(String(100), nullable=True)  # COS存储桶名称
    cos_region = Column(String(50), nullable=True)  # COS地域

    # 图片来源和类型
    source_type = Column(String(20), nullable=False, default='generated')  # generated, uploaded
    model_name = Column(String(100), nullable=True)  # 对于用户上传图片，此字段可能为空

    # 文件信息
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    mime_type = Column(String(50), nullable=True)  # MIME类型

    # 用户上传图片相关字段
    original_filename = Column(String(255), nullable=True)  # 用户上传的原始文件名
    description = Column(Text, nullable=True)  # 用户添加的描述

    # 扩展字段
    tags = Column(ARRAY(Text), nullable=True)  # 图片标签，文本数组格式
    is_public = Column(Boolean, default=False, nullable=False)  # 是否公开
    storage_status = Column(String(20), default='active', nullable=False)  # active, deleted, archived

    # 时间戳
    created_at = Column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, source_type={self.source_type}, model_name={self.model_name})>"

    @property
    def is_generated(self) -> bool:
        """是否为生成的图片"""
        return self.source_type == 'generated'

    @property
    def is_uploaded(self) -> bool:
        """是否为用户上传的图片"""
        return self.source_type == 'uploaded'

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态"""
        return self.storage_status == 'active'

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'prompt': self.prompt,
            'image_url': self.image_url,
            'url': self.image_url,  # 添加url字段，与前端接口保持一致
            'source_type': self.source_type,
            'model_name': self.model_name,
            'width': self.width,
            'height': self.height,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'original_filename': self.original_filename,
            'description': self.description,
            'tags': self.tags,
            'is_public': self.is_public,
            'storage_status': self.storage_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'cos_key': self.cos_key,
            'cos_bucket': self.cos_bucket,
            'cos_region': self.cos_region,
        }