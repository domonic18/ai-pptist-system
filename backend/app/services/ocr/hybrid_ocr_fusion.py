"""
混合OCR结果融合算法
结合传统OCR和多模态大模型的优势，提供更准确的识别结果
"""

import asyncio
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ocr.baidu_ocr_engine import BaiduOCREngine
from app.services.ocr.multimodal_ocr_engine import MultimodalOCREngine
from app.schemas.image_editing import (
    TraditionalOCRResult,
    TraditionalOCRRegion,
    MultimodalOCRResult,
    MultimodalOCRRegion,
    HybridOCRResult,
    HybridTextRegion,
    HybridOCRMetadata,
    BoundingBox,
    FontInfo,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class HybridOCRFusion:
    """
    混合OCR融合器

    结合传统OCR（精确坐标）和多模态大模型（样式信息）的优势
    """

    def __init__(self, db: AsyncSession):
        """
        初始化混合OCR融合器

        Args:
            db: 数据库会话（用于多模态OCR引擎）
        """
        self.db = db
        self.traditional_ocr = BaiduOCREngine()
        self.multimodal_ocr = MultimodalOCREngine(db=db)

    async def parse_image(
        self,
        cos_key: str,
        task_id: str,
        slide_id: str
    ) -> HybridOCRResult:
        """
        执行混合OCR识别

        Args:
            cos_key: 图片COS Key
            task_id: 任务ID
            slide_id: 幻灯片ID

        Returns:
            HybridOCRResult: 融合后的OCR结果
        """
        start_time = datetime.now()
        logger.info(
            "开始混合OCR识别",
            extra={"task_id": task_id, "slide_id": slide_id, "cos_key": cos_key}
        )

        try:
            # 步骤1: 并行执行两种OCR
            traditional_task = self._run_traditional_ocr(cos_key)
            multimodal_task = self._run_multimodal_ocr(cos_key)

            traditional_result, multimodal_result = await asyncio.gather(
                traditional_task,
                multimodal_task
            )

            # 步骤2: 融合结果
            merge_start = datetime.now()
            merged_regions = await self._merge_results(
                traditional_result.regions,
                multimodal_result.regions
            )
            merge_time = int((datetime.now() - merge_start).total_seconds() * 1000)

            # 步骤3: 构建元数据
            total_time = int((datetime.now() - start_time).total_seconds() * 1000)
            metadata = HybridOCRMetadata(
                traditional_ocr_engine=traditional_result.engine,
                multimodal_model=multimodal_result.model,
                parse_time_ms=total_time,
                traditional_time_ms=traditional_result.parse_time_ms,
                multimodal_time_ms=multimodal_result.parse_time_ms,
                merge_time_ms=merge_time,
                text_count=len(merged_regions),
                traditional_count=traditional_result.text_count,
                multimodal_count=multimodal_result.text_count,
                merged_count=len(merged_regions),
                created_at=start_time,
                completed_at=datetime.now()
            )

            result = HybridOCRResult(
                task_id=task_id,
                slide_id=slide_id,
                original_cos_key=cos_key,
                text_regions=merged_regions,
                metadata=metadata
            )

            logger.info(
                "混合OCR识别完成",
                extra={
                    "task_id": task_id,
                    "text_count": len(merged_regions),
                    "total_time_ms": total_time
                }
            )

            return result

        except Exception as e:
            logger.error(
                "混合OCR识别失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise

    async def _run_traditional_ocr(self, cos_key: str) -> TraditionalOCRResult:
        """
        运行传统OCR识别

        Args:
            cos_key: 图片COS Key

        Returns:
            TraditionalOCRResult: 传统OCR识别结果
        """
        from datetime import datetime
        start_time = datetime.now()

        regions_data = await self.traditional_ocr.parse_from_cos_key(cos_key)
        parse_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 转换为schema格式
        regions = []
        for idx, data in enumerate(regions_data):
            regions.append(TraditionalOCRRegion(
                id=f"trad_{idx:03d}",
                text=data["text"],
                bbox=BoundingBox(**data["bbox"]),
                confidence=data["confidence"]
            ))

        return TraditionalOCRResult(
            engine="baidu_ocr",
            regions=regions,
            parse_time_ms=parse_time,
            text_count=len(regions)
        )

    async def _run_multimodal_ocr(self, cos_key: str) -> MultimodalOCRResult:
        """
        运行多模态大模型OCR识别

        Args:
            cos_key: 图片COS Key

        Returns:
            MultimodalOCRResult: 多模态OCR识别结果
        """
        start_time = datetime.now()

        regions_data = await self.multimodal_ocr.parse_from_cos_key(cos_key)
        parse_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 获取使用的模型名称
        model_name = getattr(self.multimodal_ocr, "last_model_used", "gpt-4o")

        # 转换为schema格式
        regions = []
        for idx, data in enumerate(regions_data):
            font_data = data.get("font", {})
            regions.append(MultimodalOCRRegion(
                id=f"multi_{idx:03d}",
                text=data["text"],
                bbox=BoundingBox(**data["bbox"]),
                confidence=data["confidence"],
                font=FontInfo(
                    size=font_data.get("size", 16),
                    family=font_data.get("family", "Microsoft YaHei"),
                    weight=font_data.get("weight", "normal"),
                    color=font_data.get("color", "#000000"),
                    align=font_data.get("align", "left")
                )
            ))

        return MultimodalOCRResult(
            model=model_name,
            regions=regions,
            parse_time_ms=parse_time,
            text_count=len(regions)
        )

    async def _merge_results(
        self,
        traditional_regions: List[TraditionalOCRRegion],
        multimodal_regions: List[MultimodalOCRRegion]
    ) -> List[HybridTextRegion]:
        """
        融合传统OCR和多模态OCR结果

        融合策略：
        1. 文字内容：以传统OCR为准
        2. 坐标位置：使用传统OCR的精确坐标
        3. 样式信息：使用多模态大模型的识别结果
        4. 数据匹配：通过文字相似度和位置距离匹配

        Args:
            traditional_regions: 传统OCR识别结果
            multimodal_regions: 多模态OCR识别结果

        Returns:
            List[HybridTextRegion]: 融合后的文字区域列表
        """
        merged = []
        matched_multimodal_indices = set()

        # 遍历传统OCR结果
        for trad_idx, trad_region in enumerate(traditional_regions):
            # 在多模态结果中找匹配
            best_match_idx, best_match_score = await self._find_best_match(
                trad_region,
                multimodal_regions,
                matched_multimodal_indices
            )

            if best_match_idx is not None and best_match_score >= 0.7:
                # 找到匹配，使用融合结果
                multi_region = multimodal_regions[best_match_idx]
                matched_multimodal_indices.add(best_match_idx)

                merged.append(HybridTextRegion(
                    id=f"region_{len(merged) + 1:03d}",
                    text=trad_region.text,                    # 传统OCR文字
                    bbox=trad_region.bbox,                    # 传统OCR坐标
                    confidence=trad_region.confidence,
                    font=multi_region.font,                   # 多模态样式
                    color=multi_region.font.color,            # 多模态颜色
                    source="merged"
                ))
            else:
                # 没有匹配，使用传统OCR + 推断样式
                merged.append(HybridTextRegion(
                    id=f"region_{len(merged) + 1:03d}",
                    text=trad_region.text,
                    bbox=trad_region.bbox,
                    confidence=trad_region.confidence * 0.9,  # 略微降低置信度
                    font=self._infer_font_style(trad_region),
                    color=self._infer_color_from_context(trad_region),
                    source="traditional"
                ))

        # 检查多模态独有结果（传统OCR遗漏的）
        for multi_idx, multi_region in enumerate(multimodal_regions):
            if multi_idx not in matched_multimodal_indices:
                merged.append(HybridTextRegion(
                    id=f"region_{len(merged) + 1:03d}",
                    text=multi_region.text,
                    bbox=multi_region.bbox,
                    confidence=multi_region.confidence * 0.85,  # 降低置信度
                    font=multi_region.font,
                    color=multi_region.font.color,
                    source="multimodal"
                ))

        return merged

    async def _find_best_match(
        self,
        trad_region: TraditionalOCRRegion,
        multimodal_regions: List[MultimodalOCRRegion],
        used_indices: set
    ) -> Tuple[Optional[int], float]:
        """
        在多模态结果中找到最佳匹配

        Args:
            trad_region: 传统OCR区域
            multimodal_regions: 多模态OCR区域列表
            used_indices: 已使用的索引

        Returns:
            Tuple[Optional[int], float]: (最佳匹配索引, 匹配得分)
        """
        best_match_idx = None
        best_score = 0

        for idx, multi_region in enumerate(multimodal_regions):
            if idx in used_indices:
                continue

            # 文字相似度得分
            text_score = self._calculate_text_similarity(
                trad_region.text,
                multi_region.text
            )

            # 位置距离得分
            bbox_score = self._calculate_bbox_similarity(
                trad_region.bbox,
                multi_region.bbox
            )

            # 综合得分：文字内容权重更高
            combined_score = text_score * 0.6 + bbox_score * 0.4

            if combined_score > best_score:
                best_score = combined_score
                best_match_idx = idx

        return best_match_idx, best_score

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度

        使用编辑距离算法

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度 0-1
        """
        import Levenshtein

        # 计算编辑距离
        distance = Levenshtein.distance(text1, text2)
        max_len = max(len(text1), len(text2))

        if max_len == 0:
            return 1.0

        # 转换为相似度
        similarity = 1.0 - (distance / max_len)
        return similarity

    def _calculate_bbox_similarity(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """
        计算两个边界框的相似度

        基于中心点距离和面积重叠

        Args:
            bbox1: 边界框1
            bbox2: 边界框2

        Returns:
            float: 相似度 0-1
        """
        # 计算中心点
        center1_x = bbox1.x + bbox1.width / 2
        center1_y = bbox1.y + bbox1.height / 2
        center2_x = bbox2.x + bbox2.width / 2
        center2_y = bbox2.y + bbox2.height / 2

        # 中心点距离
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5

        # 归一化距离（使用较大边界框的对角线长度）
        max_diagonal = max(
            (bbox1.width ** 2 + bbox1.height ** 2) ** 0.5,
            (bbox2.width ** 2 + bbox2.height ** 2) ** 0.5
        )

        if max_diagonal == 0:
            return 1.0

        normalized_distance = distance / max_diagonal

        # 转换为相似度（距离越小相似度越高）
        similarity = max(0, 1.0 - normalized_distance)
        return similarity

    def _infer_font_style(self, region: TraditionalOCRRegion) -> FontInfo:
        """
        根据区域信息推断字体样式

        Args:
            region: 传统OCR区域

        Returns:
            FontInfo: 推断的字体信息
        """
        bbox = region.bbox
        text = region.text

        # 推断字体大小：约为高度的75%
        font_size = max(12, min(72, int(bbox.height * 0.75)))

        # 推断字重：短文字且高度大可能是标题
        is_bold = len(text) < 20 and bbox.height > 40

        return FontInfo(
            size=font_size,
            family="Microsoft YaHei",
            weight="bold" if is_bold else "normal",
            color="#000000",
            align="left"
        )

    def _infer_color_from_context(self, region: TraditionalOCRRegion) -> str:
        """
        根据上下文推断文字颜色

        简单启发式：默认黑色

        Args:
            region: 传统OCR区域

        Returns:
            str: 十六进制颜色值
        """
        return "#000000"
