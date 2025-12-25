"""
图片编辑任务Repository
提供图片编辑任务的数据库操作
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.repositories.base import BaseRepository
from app.models.image_editing_task import ImageEditingTask, EditingTaskStatus
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageEditingRepository(BaseRepository):
    """图片编辑任务Repository"""

    @property
    def model(self):
        """返回Repository对应的模型类"""
        return ImageEditingTask

    async def create_task(
        self,
        task_id: str,
        slide_id: str,
        original_cos_key: str,
        user_id: Optional[str] = None,
        edit_options: Optional[Dict] = None
    ) -> ImageEditingTask:
        """
        创建编辑任务

        Args:
            task_id: 任务ID
            slide_id: 幻灯片ID
            original_cos_key: 原始图片COS Key
            user_id: 用户ID
            edit_options: 编辑选项

        Returns:
            ImageEditingTask: 创建的任务记录
        """
        return await self.create(
            id=task_id,
            slide_id=slide_id,
            original_cos_key=original_cos_key,
            user_id=user_id,
            edit_options=edit_options,
            status=EditingTaskStatus.PENDING,
            progress=0
        )

    async def update_task_status(
        self,
        task_id: str,
        status: EditingTaskStatus,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        ocr_result: Optional[Dict] = None,
        removal_result: Optional[Dict] = None,
        edit_metadata: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[ImageEditingTask]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            current_step: 当前处理步骤
            ocr_result: OCR识别结果
            removal_result: 文字去除结果
            edit_metadata: 元数据
            error_message: 错误信息

        Returns:
            ImageEditingTask: 更新后的任务记录
        """
        update_data = {"status": status}

        if progress is not None:
            update_data["progress"] = progress

        if current_step is not None:
            update_data["current_step"] = current_step

        if ocr_result is not None:
            update_data["ocr_result"] = ocr_result

        if removal_result is not None:
            update_data["removal_result"] = removal_result

        if edit_metadata is not None:
            update_data["edit_metadata"] = edit_metadata

        if error_message is not None:
            update_data["error_message"] = error_message

        return await self.update(task_id, **update_data)

    async def get_task_by_slide_id(
        self,
        slide_id: str
    ) -> Optional[ImageEditingTask]:
        """
        根据幻灯片ID获取最新的编辑任务

        Args:
            slide_id: 幻灯片ID

        Returns:
            ImageEditingTask: 任务记录（如果存在）
        """
        try:
            query = select(ImageEditingTask).filter(
                ImageEditingTask.slide_id == slide_id
            ).order_by(ImageEditingTask.created_at.desc()).limit(1)

            result = await self.db.execute(query)
            return result.scalars().first()

        except Exception as e:
            logger.error(
                "根据幻灯片ID查询任务失败",
                extra={"slide_id": slide_id, "error": str(e)}
            )
            raise

    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[EditingTaskStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ImageEditingTask]:
        """
        获取用户的编辑任务列表

        Args:
            user_id: 用户ID
            status: 状态过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[ImageEditingTask]: 任务列表
        """
        try:
            query = select(ImageEditingTask).filter(
                ImageEditingTask.user_id == user_id
            )

            if status:
                query = query.filter(ImageEditingTask.status == status)

            query = query.order_by(
                ImageEditingTask.created_at.desc()
            ).limit(limit).offset(offset)

            result = await self.db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "获取用户任务列表失败",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise
