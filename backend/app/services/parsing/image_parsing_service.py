"""
图片解析服务
提供图片文字识别的核心业务逻辑
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image_parsing import ImageParsingRepository
from app.services.ocr.multimodal_ocr_engine import MultimodalOCREngine
from app.schemas.image_parsing import (
    TextRegion, ParseMetadata, ImageParseResult,
)
from app.models.image_parse_task import ParseTaskStatus
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageParsingService:
    """图片解析服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.repo = ImageParsingRepository(db)
        self.ocr_engine = None

    def _get_ocr_engine(self) -> MultimodalOCREngine:
        """
        获取 OCR 引擎实例（单例模式）

        Returns:
            MultimodalOCREngine: OCR引擎实例
        """
        if self.ocr_engine is None:
            self.ocr_engine = MultimodalOCREngine(self.db)
        return self.ocr_engine

    async def parse_image(
        self,
        slide_id: str,
        cos_key: str,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> ImageParseResult:
        """
        解析图片中的文字

        Args:
            slide_id: 幻灯片ID
            cos_key: 图片COS Key
            user_id: 用户ID（可选）
            task_id: 任务ID（可选，如果未提供则自动生成）

        Returns:
            ImageParseResult: 解析结果
        """
        start_time = datetime.now()
        # 如果未提供task_id，则自动生成
        if task_id is None:
            task_id = f"parse_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        logger.info(
            "开始图片解析任务",
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
                cos_key=cos_key,
                user_id=user_id
            )

        try:
            # 更新状态为处理中
            await self.repo.update_task_status(
                task_id=task_id,
                status=ParseTaskStatus.PROCESSING,
                progress=0
            )

            # 获取 OCR 引擎
            ocr_engine = self._get_ocr_engine()

            # 执行 OCR 识别（从COS Key）
            logger.info("开始OCR识别", extra={"task_id": task_id, "cos_key": cos_key})
            ocr_results = await ocr_engine.parse_from_cos_key(cos_key)
            image_width = getattr(ocr_engine, "last_image_width", None)
            image_height = getattr(ocr_engine, "last_image_height", None)

            # 构建文字区域数据
            text_regions = []
            for idx, result in enumerate(ocr_results):
                region_id = f"region_{idx + 1:03d}"

                # 从OCR结果获取字体信息（多模态模型已提供）
                bbox = result["bbox"]
                font_info = result.get("font", {
                    "size": 16,
                    "family": "Microsoft YaHei",
                    "weight": "normal",
                    "color": "#000000",
                    "align": "left"
                })

                text_region = TextRegion(
                    id=region_id,
                    text=result["text"],
                    bbox=bbox,
                    confidence=result["confidence"],
                    font=font_info
                )
                text_regions.append(text_region)

            # 计算解析耗时
            parse_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # 构建元数据
            metadata = ParseMetadata(
                parse_time=parse_time,
                ocr_engine="multimodal_ocr",
                text_count=len(text_regions),
                image_width=image_width,
                image_height=image_height,
                created_at=start_time,
                completed_at=datetime.now()
            )

            # 更新任务状态为完成
            # 使用 json.loads(metadata.json()) 确保 datetime 字段被正确序列化为字符串
            await self.repo.update_task_status(
                task_id=task_id,
                status=ParseTaskStatus.COMPLETED,
                progress=100,
                text_regions=[r.dict() for r in text_regions],
                metadata=json.loads(metadata.json())
            )

            logger.info(
                "图片解析完成",
                extra={
                    "task_id": task_id,
                    "text_count": len(text_regions),
                    "parse_time": parse_time
                }
            )

            return ImageParseResult(
                task_id=task_id,
                slide_id=slide_id,
                cos_key=cos_key,
                status=ParseTaskStatus.COMPLETED,
                progress=100,
                text_regions=text_regions,
                metadata=metadata
            )

        except Exception as e:
            logger.error("图片解析失败", extra={"task_id": task_id, "error": str(e)})

            # 更新任务状态为失败
            await self.repo.update_task_status(
                task_id=task_id,
                status=ParseTaskStatus.FAILED,
                error_message=str(e)
            )

            raise

    async def get_parse_result(self, task_id: str) -> Optional[ImageParseResult]:
        """
        获取解析结果

        Args:
            task_id: 任务ID

        Returns:
            ImageParseResult: 解析结果（如果存在）
        """
        task = await self.repo.get_by_id(task_id)

        if not task:
            return None

        # 构建响应数据
        text_regions = []
        metadata = None

        if task.text_regions:
            text_regions = [
                TextRegion(**region) for region in task.text_regions
            ]

        if task.parse_metadata:
            metadata = ParseMetadata(**task.parse_metadata)

        return ImageParseResult(
            task_id=task.id,
            slide_id=task.slide_id,
            cos_key=task.cos_key,
            status=task.status,
            progress=task.progress,
            text_regions=text_regions,
            metadata=metadata
        )

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
            "cos_key": task.cos_key,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }
