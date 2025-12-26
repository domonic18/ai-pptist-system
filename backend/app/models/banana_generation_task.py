"""
Banana生成任务和模板模型
对应数据库表：banana_generation_tasks 和 banana_templates
"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, ENUM
from app.db.database import Base


class TaskStatus(str, enum.Enum):
    """任务状态枚举（对应数据库中的banana_task_status枚举类型）"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BananaGenerationTask(Base):
    """
    Banana生成任务模型

    对应数据库表：banana_generation_tasks
    SQL脚本：docker/database/init-scripts/05_banana_generation_tables.sql
    """
    __tablename__ = "banana_generation_tasks"

    # 主键
    id = Column(String(50), primary_key=True)

    # 用户信息
    user_id = Column(String(36), nullable=True)

    # 任务配置
    outline = Column(JSONB, nullable=False)  # 大纲数据
    template_id = Column(String(50), nullable=True)  # 模板ID（自定义模板时为NULL）
    template_image_url = Column(Text, nullable=True)  # 模板图片URL（COS或本地）
    generation_model = Column(String(100), nullable=False)  # 生成模型名称
    canvas_size = Column(JSONB, nullable=False)  # 画布尺寸

    # 任务状态（使用数据库中定义的枚举类型）
    status = Column(
        ENUM('pending', 'processing', 'completed', 'failed', 'cancelled',
             name='banana_task_status', create_type=False),
        nullable=False,
        server_default='pending'
    )

    # 进度信息
    total_slides = Column(Integer, nullable=False, server_default='0')
    completed_slides = Column(Integer, nullable=False, server_default='0')
    failed_slides = Column(Integer, nullable=False, server_default='0')

    # 生成结果
    slides_data = Column(JSONB, nullable=True)  # 每页生成结果

    # 错误信息
    error_message = Column(Text, nullable=True)

    # Celery任务信息
    celery_task_id = Column(String(100), nullable=True)  # Celery任务ID
    celery_group_id = Column(String(100), nullable=True)  # Celery任务组ID

    # 时间戳（数据库触发器自动更新updated_at）
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)


class BananaTemplate(Base):
    """
    Banana模板模型

    对应数据库表：banana_templates
    SQL脚本：docker/database/init-scripts/05_banana_generation_tables.sql
    """
    __tablename__ = "banana_templates"

    # 主键
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 图片信息
    cover_url = Column(Text, nullable=False)  # 缩略图URL
    full_image_url = Column(Text, nullable=False)  # 完整图片URL

    # 模板配置
    type = Column(String(20), nullable=False, server_default='system')  # system | user
    aspect_ratio = Column(String(10), nullable=False, server_default='16:9')

    # 用户信息
    user_id = Column(String(36), nullable=True)

    # 使用统计
    usage_count = Column(Integer, nullable=False, server_default='0')

    # 状态
    is_active = Column(Boolean, nullable=False, server_default='true')

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

