"""
图片解析任务模型
对应数据库表：image_parse_tasks
"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, ENUM
from app.db.database import Base


class ParseTaskStatus(str, enum.Enum):
    """解析任务状态枚举（对应数据库中的parse_task_status枚举类型）"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageParseTask(Base):
    """
    图片解析任务模型

    对应数据库表：image_parse_tasks
    SQL脚本：docker/database/init-scripts/06_image_parsing_tables.sql
    """
    __tablename__ = "image_parse_tasks"

    # 主键
    id = Column(String(50), primary_key=True)

    # 关联信息
    slide_id = Column(String(100), nullable=False)
    cos_key = Column(Text, nullable=True)

    # 任务配置
    parse_options = Column(JSONB, nullable=True)

    # 任务状态（使用数据库中定义的枚举类型）
    status = Column(
        ENUM('pending', 'processing', 'completed', 'failed',
             name='parse_task_status', create_type=False),
        nullable=False,
        server_default='pending'
    )

    # 进度信息
    progress = Column(Integer, nullable=False, server_default='0')

    # 解析结果
    text_regions = Column(JSONB, nullable=True)
    parse_metadata = Column('metadata', JSONB, nullable=True)

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 用户关联
    user_id = Column(String(36), nullable=True)
