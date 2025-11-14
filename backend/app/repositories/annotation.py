"""
标注数据访问层
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.sql.functions import count

from app.models.annotation import AnnotationTask, SlideAnnotation
from .base import BaseRepository


class AnnotationRepository(BaseRepository):
    """标注Repository"""

    @property
    def model(self):
        return AnnotationTask

    async def create_annotation_task(
        self,
        user_id: str,
        presentation_id: str,
        model_id: Optional[str] = None,
        model_config: Optional[Dict[str, Any]] = None,
        extraction_config: Optional[Dict[str, Any]] = None
    ) -> AnnotationTask:
        """创建标注任务记录"""
        return await self.create(
            user_id=user_id,
            presentation_id=presentation_id,
            model_id=model_id,
            model_config=model_config,
            extraction_config=extraction_config,
            status="pending",
            total_pages=0,
            completed_pages=0,
            failed_pages=0,
            average_confidence=0.0,
            total_corrections=0
        )

    async def get_annotation_task_by_id(self, task_id: str) -> Optional[AnnotationTask]:
        """根据ID获取标注任务"""
        stmt = select(AnnotationTask).where(AnnotationTask.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_annotation_tasks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[AnnotationTask], int]:
        """获取用户的标注任务列表"""
        stmt = (
            select(AnnotationTask)
            .where(AnnotationTask.user_id == user_id)
            .order_by(desc(AnnotationTask.created_at))
            .offset(skip)
            .limit(limit)
        )

        count_stmt = select(count(AnnotationTask.id)).where(AnnotationTask.user_id == user_id)

        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(tasks), total

    async def update_annotation_task_status(
        self,
        task_id: str,
        status: str,
        completed_pages: Optional[int] = None,
        failed_pages: Optional[int] = None,
        average_confidence: Optional[float] = None
    ) -> Optional[AnnotationTask]:
        """更新标注任务状态"""
        update_data = {"status": status}

        if completed_pages is not None:
            update_data["completed_pages"] = completed_pages
        if failed_pages is not None:
            update_data["failed_pages"] = failed_pages
        if average_confidence is not None:
            update_data["average_confidence"] = average_confidence

        return await self.update(task_id, update_data)

    async def create_slide_annotation(
        self,
        task_id: str,
        slide_id: str,
        slide_index: int,
        page_type: Optional[str] = None,
        page_type_confidence: Optional[float] = None,
        page_type_reason: Optional[str] = None,
        layout_type: Optional[str] = None,
        layout_type_confidence: Optional[float] = None,
        layout_type_reason: Optional[str] = None,
        element_annotations: Optional[Dict[str, Any]] = None,
        overall_confidence: Optional[float] = None
    ) -> SlideAnnotation:
        """创建幻灯片标注记录"""
        slide_annotation = SlideAnnotation(
            task_id=task_id,
            slide_id=slide_id,
            slide_index=slide_index,
            page_type=page_type,
            page_type_confidence=page_type_confidence,
            page_type_reason=page_type_reason,
            layout_type=layout_type,
            layout_type_confidence=layout_type_confidence,
            layout_type_reason=layout_type_reason,
            element_annotations=element_annotations,
            overall_confidence=overall_confidence
        )

        self.db.add(slide_annotation)
        await self.db.commit()
        await self.db.refresh(slide_annotation)
        return slide_annotation

    async def get_slide_annotation_by_id(self, annotation_id: str) -> Optional[SlideAnnotation]:
        """根据ID获取幻灯片标注"""
        stmt = select(SlideAnnotation).where(SlideAnnotation.id == annotation_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_slide_annotations_by_task(
        self,
        task_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[SlideAnnotation], int]:
        """获取任务的幻灯片标注列表"""
        stmt = (
            select(SlideAnnotation)
            .where(SlideAnnotation.task_id == task_id)
            .order_by(SlideAnnotation.slide_index)
            .offset(skip)
            .limit(limit)
        )

        count_stmt = select(count(SlideAnnotation.id)).where(SlideAnnotation.task_id == task_id)

        result = await self.db.execute(stmt)
        annotations = result.scalars().all()

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        return list(annotations), total

    async def get_slide_annotation_by_slide(
        self,
        task_id: str,
        slide_id: str
    ) -> Optional[SlideAnnotation]:
        """根据任务ID和幻灯片ID获取标注"""
        stmt = select(SlideAnnotation).where(
            SlideAnnotation.task_id == task_id,
            SlideAnnotation.slide_id == slide_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_slide_annotation(
        self,
        annotation_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[SlideAnnotation]:
        """更新幻灯片标注"""
        stmt = select(SlideAnnotation).where(SlideAnnotation.id == annotation_id)
        result = await self.db.execute(stmt)
        annotation = result.scalar_one_or_none()

        if annotation:
            for key, value in update_data.items():
                if hasattr(annotation, key):
                    setattr(annotation, key, value)

            await self.db.commit()
            await self.db.refresh(annotation)
            return annotation

        return None

    async def delete_slide_annotation(self, annotation_id: str) -> bool:
        """删除幻灯片标注"""
        stmt = select(SlideAnnotation).where(SlideAnnotation.id == annotation_id)
        result = await self.db.execute(stmt)
        annotation = result.scalar_one_or_none()

        if annotation:
            await self.db.delete(annotation)
            await self.db.commit()
            return True

        return False