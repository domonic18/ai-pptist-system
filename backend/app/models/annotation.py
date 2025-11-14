"""
标注数据模型
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.db.database import Base


class AnnotationTaskStatus(str, PyEnum):
    """标注任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnnotationTask(Base):
    """标注任务表"""
    __tablename__ = "annotation_tasks"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    presentation_id = Column(String(50), nullable=False, index=True)
    status = Column(Enum(AnnotationTaskStatus), default=AnnotationTaskStatus.PENDING, index=True)

    # 任务配置
    model_id = Column(String(50), nullable=True, comment="使用的AI模型ID")
    model_config = Column(JSONB, nullable=True, comment="模型配置")
    extraction_config = Column(JSONB, nullable=True, comment="提取配置")

    # 进度信息
    total_pages = Column(Integer, default=0, comment="总页数")
    completed_pages = Column(Integer, default=0, comment="已完成页数")
    failed_pages = Column(Integer, default=0, comment="失败页数")

    # 统计信息
    average_confidence = Column(Float, default=0.0, comment="平均置信度")
    total_corrections = Column(Integer, default=0, comment="总修正数")

    # 时间信息
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
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "presentation_id": self.presentation_id,
            "status": self.status.value,
            "model_id": self.model_id,
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "failed_pages": self.failed_pages,
            "average_confidence": self.average_confidence,
            "total_corrections": self.total_corrections,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class SlideAnnotation(Base):
    """幻灯片标注结果表"""
    __tablename__ = "slide_annotations"

    id = Column(String(50), primary_key=True)
    task_id = Column(String(50), nullable=False, index=True)
    slide_id = Column(String(50), nullable=False, index=True)
    slide_index = Column(Integer, nullable=False, comment="幻灯片索引")

    # 页面类型
    page_type = Column(String(50), nullable=True, comment="页面类型")
    page_type_confidence = Column(Float, nullable=True, comment="页面类型置信度")
    page_type_reason = Column(String(500), nullable=True, comment="页面类型识别依据")

    # 布局类型
    layout_type = Column(String(50), nullable=True, comment="布局类型")
    layout_type_confidence = Column(Float, nullable=True, comment="布局类型置信度")
    layout_type_reason = Column(String(500), nullable=True, comment="布局类型识别依据")

    # 元素标注（JSON格式）
    element_annotations = Column(JSONB, nullable=True, comment="元素标注列表")

    # 整体置信度
    overall_confidence = Column(Float, nullable=True, comment="整体置信度")

    # 用户修正
    user_corrections = Column(JSONB, nullable=True, comment="用户修正记录")
    has_corrections = Column(Integer, default=0, comment="是否有修正")

    # 时间信息
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

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "slide_id": self.slide_id,
            "slide_index": self.slide_index,
            "page_type": {
                "type": self.page_type,
                "confidence": self.page_type_confidence,
                "reason": self.page_type_reason
            },
            "layout_type": {
                "type": self.layout_type,
                "confidence": self.layout_type_confidence,
                "reason": self.layout_type_reason
            },
            "element_annotations": self.element_annotations,
            "overall_confidence": self.overall_confidence,
            "user_corrections": self.user_corrections,
            "has_corrections": self.has_corrections == 1,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }