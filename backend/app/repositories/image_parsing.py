"""
图片解析任务数据访问层
提供图片解析任务的数据库操作
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.repositories.base import BaseRepository
from app.models.image_parse_task import ImageParseTask, ParseTaskStatus
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageParsingRepository(BaseRepository):
    """图片解析任务Repository"""

    @property
    def model(self):
        """返回Repository对应的模型类"""
        return ImageParseTask

    async def create_task(
        self,
        task_id: str,
        slide_id: str,
        cos_key: Optional[str] = None,
        user_id: Optional[str] = None,
        parse_options: Optional[Dict] = None
    ) -> ImageParseTask:
        """
        创建解析任务

        Args:
            task_id: 任务ID
            slide_id: 幻灯片ID
            cos_key: 图片COS Key（可选）
            user_id: 用户ID
            parse_options: 解析选项

        Returns:
            ImageParseTask: 创建的任务记录
        """
        return await self.create(
            id=task_id,
            slide_id=slide_id,
            cos_key=cos_key,
            user_id=user_id,
            parse_options=parse_options,
            status=ParseTaskStatus.PENDING,
            progress=0
        )

    async def update_task_status(
        self,
        task_id: str,
        status: ParseTaskStatus,
        progress: Optional[int] = None,
        text_regions: Optional[list] = None,
        metadata: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[ImageParseTask]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            text_regions: 解析出的文字区域
            metadata: 解析元数据
            error_message: 错误信息

        Returns:
            ImageParseTask: 更新后的任务记录
        """
        update_data = {"status": status}

        if progress is not None:
            update_data["progress"] = progress

        if text_regions is not None:
            update_data["text_regions"] = text_regions

        if metadata is not None:
            update_data["parse_metadata"] = metadata

        if error_message is not None:
            update_data["error_message"] = error_message

        return await self.update(task_id, **update_data)

    async def get_task_by_slide_id(
        self,
        slide_id: str
    ) -> Optional[ImageParseTask]:
        """
        根据幻灯片ID获取最新的解析任务

        Args:
            slide_id: 幻灯片ID

        Returns:
            ImageParseTask: 任务记录（如果存在）
        """
        try:
            query = select(ImageParseTask).filter(
                ImageParseTask.slide_id == slide_id
            ).order_by(ImageParseTask.created_at.desc()).limit(1)

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
        status: Optional[ParseTaskStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[ImageParseTask]:
        """
        获取用户的解析任务列表

        Args:
            user_id: 用户ID
            status: 状态过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            list[ImageParseTask]: 任务列表
        """
        try:
            query = select(ImageParseTask).filter(
                ImageParseTask.user_id == user_id
            )

            if status:
                query = query.filter(ImageParseTask.status == status)

            query = query.order_by(
                ImageParseTask.created_at.desc()
            ).limit(limit).offset(offset)

            result = await self.db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(
                "获取用户任务列表失败",
                extra={"user_id": user_id, "error": str(e)}
            )
            raise
