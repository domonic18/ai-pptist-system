"""
MinerU + 多模态混合识别服务
MinerU提供精确坐标，多模态大模型提供样式信息
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.config import settings
from app.services.ocr.mineru_adapter import MinerUAdapter, convert_bbox_from_normalized
from app.services.ocr.multimodal_ocr_engine import MultimodalOCREngine
from app.schemas.image_editing import (
    HybridOCRResult,
    HybridTextRegion,
    HybridOCRMetadata,
    BoundingBox,
    FontInfo,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class MinerUMultimodalFusionService:
    """
    MinerU + 多模态混合识别服务

    由于MinerU不提供样式信息，需要与多模态大模型融合：
    - MinerU: 精确的文字坐标 + 装饰元素识别
    - 多模态: 文字样式信息（字体、颜色、大小）
    """

    def __init__(self, db: AsyncSession):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.mineru_adapter = MinerUAdapter()
        self.multimodal_engine = MultimodalOCREngine(db=db)

    async def recognize_image(
        self,
        cos_key: str,
        task_id: str,
        slide_id: str,
        enable_formula: bool = True,
        enable_table: bool = True,
        enable_style_recognition: bool = True
    ) -> HybridOCRResult:
        """
        使用MinerU + 多模态混合识别

        Args:
            cos_key: 图片COS Key
            task_id: 任务ID
            slide_id: 幻灯片ID
            enable_formula: 是否识别公式
            enable_table: 是否识别表格
            enable_style_recognition: 是否启用样式识别（多模态）

        Returns:
            HybridOCRResult: 融合识别结果
        """
        start_time = datetime.now()

        logger.info(
            "开始MinerU+多模态混合识别",
            extra={
                "task_id": task_id,
                "slide_id": slide_id,
                "cos_key": cos_key,
                "enable_style_recognition": enable_style_recognition
            }
        )

        try:
            # 步骤1: 并行执行MinerU和多模态识别
            mineru_task = self._recognize_with_mineru(
                cos_key,
                enable_formula,
                enable_table
            )

            multimodal_task = self._recognize_with_multimodal(
                cos_key
            ) if enable_style_recognition else None

            # 等待MinerU完成
            mineru_result = await mineru_task

            # 如果启用样式识别，等待多模态完成
            multimodal_result = None
            if enable_style_recognition and multimodal_task:
                multimodal_result = await multimodal_task

            # 步骤2: 融合结果
            merge_start = datetime.now()
            fused_regions = self._fuse_results(
                mineru_result,
                multimodal_result
            )
            merge_time = int((datetime.now() - merge_start).total_seconds() * 1000)

            # 步骤3: 构建元数据
            total_time = int((datetime.now() - start_time).total_seconds() * 1000)

            metadata = HybridOCRMetadata(
                traditional_ocr_engine="mineru",
                multimodal_model=multimodal_result.get("model", "gpt-4o") if multimodal_result else "none",
                parse_time_ms=total_time,
                traditional_time_ms=mineru_result.get("parse_time_ms", 0),
                multimodal_time_ms=multimodal_result.get("parse_time_ms", 0) if multimodal_result else 0,
                merge_time_ms=merge_time,
                text_count=len(fused_regions),
                traditional_count=len(mineru_result.get("text_regions", [])),
                multimodal_count=len(multimodal_result.get("regions", [])) if multimodal_result else 0,
                merged_count=len(fused_regions),
                created_at=start_time,
                completed_at=datetime.now()
            )

            result = HybridOCRResult(
                task_id=task_id,
                slide_id=slide_id,
                original_cos_key=cos_key,
                text_regions=fused_regions,
                metadata=metadata
            )

            logger.info(
                "MinerU+多模态混合识别完成",
                extra={
                    "task_id": task_id,
                    "text_count": len(fused_regions),
                    "image_count": len(mineru_result.get("image_regions", [])),
                    "total_time_ms": total_time
                }
            )

            return result

        except Exception as e:
            logger.error(
                "MinerU+多模态混合识别失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise

    async def _recognize_with_mineru(
        self,
        cos_key: str,
        enable_formula: bool,
        enable_table: bool
    ) -> Dict[str, Any]:
        """
        使用MinerU识别（获取精确坐标和装饰元素）

        Args:
            cos_key: 图片COS Key
            enable_formula: 是否识别公式
            enable_table: 是否识别表格

        Returns:
            Dict: MinerU识别结果
        """
        result = await self.mineru_adapter.recognize_from_cos_key(
            cos_key=cos_key,
            enable_ocr=True,
            enable_formula=enable_formula,
            enable_table=enable_table
        )

        # 格式化结果
        return self.mineru_adapter.format_mineru_result(result, cos_key)

    async def _recognize_with_multimodal(
        self,
        cos_key: str
    ) -> Dict[str, Any]:
        """
        使用多模态大模型识别（获取样式信息）

        Args:
            cos_key: 图片COS Key

        Returns:
            Dict: 多模态识别结果
        """
        start_time = datetime.now()

        regions_data = await self.multimodal_engine.parse_from_cos_key(cos_key)
        parse_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 获取使用的模型名称
        model_name = getattr(self.multimodal_engine, "last_model_used", "gpt-4o")

        return {
            "model": model_name,
            "regions": regions_data,
            "parse_time_ms": parse_time
        }

    def _fuse_results(
        self,
        mineru_result: Dict[str, Any],
        multimodal_result: Optional[Dict[str, Any]]
    ) -> List[HybridTextRegion]:
        """
        融合MinerU和多模态结果

        融合策略：
        1. 文字坐标：使用MinerU的精确坐标
        2. 文字内容：使用MinerU的文字（更准确）
        3. 样式信息：通过位置匹配从多模态结果获取

        Args:
            mineru_result: MinerU识别结果
            multimodal_result: 多模态识别结果（可选）

        Returns:
            List[HybridTextRegion]: 融合后的文字区域列表
        """
        mineru_texts = mineru_result.get("text_regions", [])
        multimodal_regions = multimodal_result.get("regions", []) if multimodal_result else []

        fused = []
        used_multimodal_indices = set()

        for idx, mineru_text in enumerate(mineru_texts):
            # 获取MinerU的bbox
            mineru_bbox = mineru_text.get("bbox", {})

            # 查找匹配的多模态样式
            matched_style = None
            best_score = 0
            best_idx = -1

            for mm_idx, mm_region in enumerate(multimodal_regions):
                if mm_idx in used_multimodal_indices:
                    continue

                mm_bbox = mm_region.get("bbox", {})

                # 计算位置相似度
                score = self._calculate_position_similarity(mineru_bbox, mm_bbox)

                if score > best_score and score > 0.5:
                    best_score = score
                    best_idx = mm_idx
                    matched_style = mm_region.get("font", {})

            if best_idx >= 0:
                used_multimodal_indices.add(best_idx)

            # 构建融合结果
            fused.append(HybridTextRegion(
                id=f"region_{len(fused) + 1:03d}",
                text=mineru_text.get("text", ""),
                bbox=BoundingBox(**mineru_bbox),
                confidence=0.95,
                font=FontInfo(
                    size=matched_style.get("size", 16) if matched_style else 16,
                    family=matched_style.get("family", "Microsoft YaHei") if matched_style else "Microsoft YaHei",
                    weight=matched_style.get("weight", "normal") if matched_style else "normal",
                    color=matched_style.get("color", "#000000") if matched_style else "#000000",
                    align=matched_style.get("align", "left") if matched_style else "left"
                ),
                color=matched_style.get("color", "#000000") if matched_style else "#000000",
                source="mineru_multimodal_fusion" if matched_style else "mineru"
            ))

        return fused

    def _calculate_position_similarity(
        self,
        bbox1: Dict[str, Any],
        bbox2: Dict[str, Any]
    ) -> float:
        """
        计算两个边界框的位置相似度

        基于中心点距离

        Args:
            bbox1: 边界框1
            bbox2: 边界框2

        Returns:
            float: 相似度 0-1
        """
        # 计算中心点
        center1_x = bbox1.get("x", 0) + bbox1.get("width", 0) / 2
        center1_y = bbox1.get("y", 0) + bbox1.get("height", 0) / 2
        center2_x = bbox2.get("x", 0) + bbox2.get("width", 0) / 2
        center2_y = bbox2.get("y", 0) + bbox2.get("height", 0) / 2

        # 中心点距离
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5

        # 归一化距离（使用较大边界框的对角线长度）
        max_diagonal = max(
            (bbox1.get("width", 0) ** 2 + bbox1.get("height", 0) ** 2) ** 0.5,
            (bbox2.get("width", 0) ** 2 + bbox2.get("height", 0) ** 2) ** 0.5
        )

        if max_diagonal == 0:
            return 1.0

        normalized_distance = distance / max_diagonal

        # 转换为相似度（距离越小相似度越高）
        similarity = max(0, 1.0 - normalized_distance)
        return similarity

    def get_image_regions(
        self,
        mineru_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        获取装饰元素区域

        Args:
            mineru_result: MinerU识别结果

        Returns:
            List[Dict]: 装饰元素区域列表
        """
        return mineru_result.get("image_regions", [])

    def get_metadata(
        self,
        mineru_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取识别元数据

        Args:
            mineru_result: MinerU识别结果

        Returns:
            Dict: 元数据
        """
        return mineru_result.get("metadata", {})
