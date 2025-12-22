"""
Banana生成任务仓库
提供对Banana生成任务和模板的数据库操作
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.banana_generation_task import BananaGenerationTask, BananaTemplate, TaskStatus
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class BananaGenerationRepository:
    """Banana生成任务仓库"""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        task_id: str,
        outline: Dict[str, Any],
        template_id: str,
        template_image_url: str,
        generation_model: str,
        canvas_size: Dict[str, int],
        total_slides: int,
        user_id: Optional[str] = None
    ) -> BananaGenerationTask:
        """
        创建生成任务记录

        Args:
            task_id: 任务ID
            outline: 大纲数据
            template_id: 模板ID
            template_image_url: 模板图片URL
            generation_model: 生成模型名称
            canvas_size: 画布尺寸
            total_slides: 总幻灯片数
            user_id: 用户ID（可选）

        Returns:
            BananaGenerationTask: 创建的任务对象
        """
        task = BananaGenerationTask(
            id=task_id,
            user_id=user_id,
            outline=outline,
            template_id=template_id,
            template_image_url=template_image_url,
            generation_model=generation_model,
            canvas_size=canvas_size,
            status=TaskStatus.PENDING,
            total_slides=total_slides,
            completed_slides=0,
            failed_slides=0,
            slides_data={"slides": []}
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info("创建Banana生成任务", extra={
            "task_id": task_id,
            "template_id": template_id,
            "total_slides": total_slides
        })

        return task

    def get_task(self, task_id: str) -> Optional[BananaGenerationTask]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            BananaGenerationTask: 任务对象，如果不存在返回None
        """
        return self.db.query(BananaGenerationTask).filter(
            BananaGenerationTask.id == task_id
        ).first()

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        celery_task_id: Optional[str] = None,
        celery_group_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[BananaGenerationTask]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            celery_task_id: Celery任务ID
            celery_group_id: Celery任务组ID
            error_message: 错误信息

        Returns:
            BananaGenerationTask: 更新后的任务对象，如果不存在返回None
        """
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"任务未找到: {task_id}")
            return None

        task.status = status

        if celery_task_id:
            task.celery_task_id = celery_task_id
        if celery_group_id:
            task.celery_group_id = celery_group_id
        if error_message:
            task.error_message = error_message

        # 记录开始和完成时间
        from datetime import datetime
        if status == TaskStatus.PROCESSING and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(task)

        logger.info("更新任务状态", extra={
            "task_id": task_id,
            "status": status,
            "celery_task_id": celery_task_id
        })

        return task

    def update_task_progress(
        self,
        task_id: str,
        completed_slides: int,
        failed_slides: int
    ) -> Optional[BananaGenerationTask]:
        """
        更新任务进度

        Args:
            task_id: 任务ID
            completed_slides: 已完成幻灯片数
            failed_slides: 失败幻灯片数

        Returns:
            BananaGenerationTask: 更新后的任务对象
        """
        task = self.get_task(task_id)
        if not task:
            return None

        task.completed_slides = completed_slides
        task.failed_slides = failed_slides

        # 更新状态
        total = task.total_slides
        if completed_slides + failed_slides == total:
            task.status = TaskStatus.COMPLETED if failed_slides == 0 else TaskStatus.COMPLETED
        elif completed_slides > 0 or failed_slides > 0:
            task.status = TaskStatus.PROCESSING

        self.db.commit()
        self.db.refresh(task)

        return task

    def update_slides_data(
        self,
        task_id: str,
        slides_data: Dict[str, Any]
    ) -> Optional[BananaGenerationTask]:
        """
        更新幻灯片生成结果数据

        Args:
            task_id: 任务ID
            slides_data: 幻灯片数据

        Returns:
            BananaGenerationTask: 更新后的任务对象
        """
        task = self.get_task(task_id)
        if not task:
            return None

        task.slides_data = slides_data
        self.db.commit()
        self.db.refresh(task)

        return task

    def get_user_tasks(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[BananaGenerationTask]:
        """
        获取用户的生成任务列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[BananaGenerationTask]: 任务列表
        """
        return self.db.query(BananaGenerationTask).filter(
            BananaGenerationTask.user_id == user_id
        ).order_by(
            desc(BananaGenerationTask.created_at)
        ).limit(limit).offset(offset).all()

    def get_active_tasks_count(self, user_id: Optional[str] = None) -> int:
        """
        获取活跃的生成任务数量

        Args:
            user_id: 用户ID（可选，不指定则统计所有用户）

        Returns:
            int: 活跃任务数量
        """
        query = self.db.query(BananaGenerationTask).filter(
            BananaGenerationTask.status.in_([
                TaskStatus.PENDING,
                TaskStatus.PROCESSING
            ])
        )

        if user_id:
            query = query.filter(BananaGenerationTask.user_id == user_id)

        return query.count()

    # Template methods
    def create_template(
        self,
        template_id: str,
        name: str,
        cover_url: str,
        full_image_url: str,
        type: str = "system",
        aspect_ratio: str = "16:9",
        description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> BananaTemplate:
        """
        创建模板记录

        Args:
            template_id: 模板ID
            name: 模板名称
            cover_url: 缩略图URL
            full_image_url: 完整图片URL
            type: 模板类型（system|user）
            aspect_ratio: 宽高比
            description: 描述
            user_id: 用户ID（用户上传时使用）

        Returns:
            BananaTemplate: 创建的模板对象
        """
        template = BananaTemplate(
            id=template_id,
            name=name,
            description=description,
            cover_url=cover_url,
            full_image_url=full_image_url,
            type=type,
            aspect_ratio=aspect_ratio,
            user_id=user_id
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        logger.info("创建Banana模板", extra={
            "template_id": template_id,
            "name": name,
            "type": type
        })

        return template

    def get_template(self, template_id: str) -> Optional[BananaTemplate]:
        """
        获取模板详情

        Args:
            template_id: 模板ID

        Returns:
            BananaTemplate: 模板对象，如果不存在返回None
        """
        return self.db.query(BananaTemplate).filter(
            BananaTemplate.id == template_id,
            BananaTemplate.is_active == True
        ).first()

    def get_templates(
        self,
        type: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        limit: int = 100
    ) -> List[BananaTemplate]:
        """
        获取模板列表

        Args:
            type: 模板类型（system|user）
            aspect_ratio: 宽高比（16:9|4:3）
            limit: 返回数量限制

        Returns:
            List[BananaTemplate]: 模板列表
        """
        query = self.db.query(BananaTemplate).filter(
            BananaTemplate.is_active == True
        )

        if type:
            query = query.filter(BananaTemplate.type == type)
        if aspect_ratio:
            query = query.filter(BananaTemplate.aspect_ratio == aspect_ratio)

        return query.order_by(
            desc(BananaTemplate.usage_count),
            desc(BananaTemplate.created_at)
        ).limit(limit).all()

    def increment_template_usage(self, template_id: str) -> bool:
        """
        增加模板使用次数

        Args:
            template_id: 模板ID

        Returns:
            bool: 是否成功
        """
        template = self.get_template(template_id)
        if not template:
            return False

        template.usage_count += 1
        self.db.commit()

        return True

    def delete_template(self, template_id: str) -> bool:
        """
        删除模板（软删除）

        Args:
            template_id: 模板ID

        Returns:
            bool: 是否成功
        """
        template = self.get_template(template_id)
        if not template:
            return False

        template.is_active = False
        self.db.commit()

        logger.info("删除Banana模板", extra={
            "template_id": template_id
        })

        return True
