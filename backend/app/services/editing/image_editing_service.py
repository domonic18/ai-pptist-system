"""
图片编辑服务
提供混合OCR识别和文字去除的核心业务逻辑
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image_editing import ImageEditingRepository
from app.services.ocr.hybrid_ocr_fusion import HybridOCRFusion
from app.services.editing.text_removal_service import TextRemovalService
from app.models.image_editing_task import EditingTaskStatus
from app.schemas.image_editing import (
    HybridOCRResult,
    TextRemovalResult,
    EditingTaskMetadata,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageEditingService:
    """图片编辑服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.repo = ImageEditingRepository(db)
        self.ocr_fusion = None
        self.text_removal_service = None

    def _get_ocr_fusion(self) -> HybridOCRFusion:
        """
        获取OCR融合器实例（单例模式）

        Returns:
            HybridOCRFusion: OCR融合器实例
        """
        if self.ocr_fusion is None:
            self.ocr_fusion = HybridOCRFusion(db=self.db)
        return self.ocr_fusion

    def _get_text_removal_service(self) -> TextRemovalService:
        """
        获取文字去除服务实例（单例模式）

        Returns:
            TextRemovalService: 文字去除服务实例
        """
        if self.text_removal_service is None:
            self.text_removal_service = TextRemovalService(db=self.db)
        return self.text_removal_service

    async def parse_with_hybrid_ocr(
        self,
        slide_id: str,
        cos_key: str,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> HybridOCRResult:
        """
        使用混合OCR识别图片中的文字

        Args:
            slide_id: 幻灯片ID
            cos_key: 图片COS Key
            user_id: 用户ID（可选）
            task_id: 任务ID（可选，如果未提供则自动生成）

        Returns:
            HybridOCRResult: 混合OCR识别结果
        """
        start_time = datetime.now()

        # 如果未提供task_id，则自动生成
        if task_id is None:
            task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(
            "开始混合OCR识别任务",
            extra={
                "task_id": task_id,
                "slide_id": slide_id,
                "cos_key": cos_key
            }
        )

        # 仅在task_id不存在时创建新任务记录（避免重复创建）
        existing_task = await self.repo.get_by_id(task_id)
        if not existing_task:
            await self.repo.create_task(
                task_id=task_id,
                slide_id=slide_id,
                original_cos_key=cos_key,
                user_id=user_id
            )

        try:
            # 更新状态为OCR处理中
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.OCR_PROCESSING,
                progress=10
            )

            # 获取OCR融合器
            ocr_fusion = self._get_ocr_fusion()

            # 执行混合OCR识别
            logger.info("开始混合OCR识别", extra={"task_id": task_id, "cos_key": cos_key})
            result = await ocr_fusion.parse_image(
                cos_key=cos_key,
                task_id=task_id,
                slide_id=slide_id
            )

            # 更新任务状态
            # 使用 json.loads(result.json()) 确保 datetime 字段被正确序列化为字符串
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.COMPLETED,
                progress=50,  # OCR完成，进度50%
                ocr_result=json.loads(result.json())
            )

            logger.info(
                "混合OCR识别完成",
                extra={
                    "task_id": task_id,
                    "text_count": len(result.text_regions),
                    "parse_time": result.metadata.parse_time_ms
                }
            )

            return result

        except Exception as e:
            logger.error("混合OCR识别失败", extra={"task_id": task_id, "error": str(e)})

            # 更新任务状态为失败
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.FAILED,
                error_message=str(e)
            )

            raise

    async def get_parse_result(self, task_id: str) -> Optional[HybridOCRResult]:
        """
        获取OCR识别结果

        Args:
            task_id: 任务ID

        Returns:
            HybridOCRResult: OCR识别结果（如果存在）
        """
        task = await self.repo.get_by_id(task_id)

        if not task:
            return None

        # 构建响应数据
        if task.ocr_result:
            return HybridOCRResult(**task.ocr_result)

        return None

    async def get_editing_result(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取完整的编辑结果

        Args:
            task_id: 任务ID

        Returns:
            Dict: 编辑结果（如果存在）
        """
        task = await self.repo.get_by_id(task_id)

        if not task:
            return None

        # 构建响应数据
        result = {
            "task_id": task.id,
            "slide_id": task.slide_id,
            "original_cos_key": task.original_cos_key,
            "edited_cos_key": task.edited_cos_key,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
        }

        # 添加OCR结果
        if task.ocr_result:
            result["ocr_result"] = task.ocr_result

        # 添加文字去除结果
        if task.removal_result:
            result["edited_image"] = task.removal_result

        # 添加元数据
        if task.edit_metadata:
            result["metadata"] = task.edit_metadata

        # 添加错误信息
        if task.error_message:
            result["error_message"] = task.error_message

        return result

    async def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态（轻量级查询）

        Args:
            task_id: 任务ID

        Returns:
            Dict: 任务状态信息
        """
        task = await self.repo.get_by_id(task_id)

        if not task:
            return None

        return {
            "task_id": task.id,
            "slide_id": task.slide_id,
            "original_cos_key": task.original_cos_key,
            "edited_cos_key": task.edited_cos_key,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }

    async def remove_text_from_image(
        self,
        slide_id: str,
        cos_key: str,
        ai_model_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        ocr_result: Optional[HybridOCRResult] = None
    ) -> Dict[str, Any]:
        """
        使用文生图去除图片中的文字

        Args:
            slide_id: 幻灯片ID
            cos_key: 图片COS Key
            ai_model_id: AI模型ID（可选，如果不提供则使用默认模型）
            user_id: 用户ID（可选）
            task_id: 任务ID（可选，如果未提供则自动生成）
            ocr_result: OCR识别结果（可选，用于优化提示词）

        Returns:
            Dict: 去除文字结果
        """
        start_time = datetime.now()

        # 如果未提供task_id，则自动生成
        if task_id is None:
            task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(
            "开始文字去除任务",
            extra={
                "task_id": task_id,
                "slide_id": slide_id,
                "cos_key": cos_key,
                "ai_model_id": ai_model_id
            }
        )

        # 仅在task_id不存在时创建新任务记录
        existing_task = await self.repo.get_by_id(task_id)
        if not existing_task:
            await self.repo.create_task(
                task_id=task_id,
                slide_id=slide_id,
                original_cos_key=cos_key,
                user_id=user_id
            )

        try:
            # 更新状态为文字去除中
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.TEXT_REMOVAL,
                progress=50,
                current_step="removing_text_via_ai"
            )

            # 获取文字去除服务
            text_removal_service = self._get_text_removal_service()

            # 获取文字数量（用于优化提示词）
            text_count = len(ocr_result.text_regions) if ocr_result else 0

            # 执行文字去除
            logger.info("开始执行文字去除", extra={"task_id": task_id, "cos_key": cos_key})
            removal_result = await text_removal_service.remove_text_from_image(
                original_cos_key=cos_key,
                ai_model_id=ai_model_id,
                text_count=text_count
            )

            # 更新任务状态为完成
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.COMPLETED,
                progress=100,
                removal_result=removal_result
            )

            logger.info(
                "文字去除完成",
                extra={
                    "task_id": task_id,
                    "edited_cos_key": removal_result["edited_cos_key"],
                    "processing_time": removal_result["processing_time_ms"]
                }
            )

            return removal_result

        except Exception as e:
            logger.error("文字去除失败", extra={"task_id": task_id, "error": str(e)})

            # 更新任务状态为失败
            await self.repo.update_task_status(
                task_id=task_id,
                status=EditingTaskStatus.FAILED,
                error_message=str(e)
            )

            raise
