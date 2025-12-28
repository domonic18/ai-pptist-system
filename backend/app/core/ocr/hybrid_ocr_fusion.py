"""
混合OCR结果融合算法
结合传统OCR和多模态大模型的优势，提供更准确的识别结果

功能改进：
1. 文字去重：使用IoU、文本相似度、中心点距离三重检测
2. 坐标准确性：考虑object-fit模式和文本盒模型补偿
"""

import asyncio
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ocr.baidu_ocr_engine import BaiduOCREngine
from app.core.ocr.multimodal_ocr_engine import MultimodalOCREngine
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


# ============================================================================
# 文字去重器
# ============================================================================

class TextDeduplicator:
    """
    文字去重器

    使用多重策略确保文字不会重复：
    1. IoU (Intersection over Union) 重叠检测
    2. 文字内容相似度检测
    3. 中心点距离检测
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        text_similarity_threshold: float = 0.85,
        distance_threshold: float = 50.0
    ):
        """
        初始化去重器

        Args:
            iou_threshold: IoU阈值，超过此值认为重叠
            text_similarity_threshold: 文本相似度阈值
            distance_threshold: 中心点距离阈值（像素）
        """
        self.iou_threshold = iou_threshold
        self.text_similarity_threshold = text_similarity_threshold
        self.distance_threshold = distance_threshold

    def is_duplicate(
        self,
        region: HybridTextRegion,
        existing_regions: List[HybridTextRegion]
    ) -> Tuple[bool, Optional[HybridTextRegion]]:
        """
        检查区域是否与已存在区域重复

        Args:
            region: 待检测区域
            existing_regions: 已存在的区域列表

        Returns:
            (is_duplicate, matched_region): 是否重复，匹配的已存在区域
        """
        for existing in existing_regions:
            # 策略1: 检测bbox重叠 (IoU)
            iou = self._calculate_iou(region.bbox, existing.bbox)
            if iou > self.iou_threshold:
                # 有重叠，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    region.text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    logger.debug(
                        "检测到重复文字（IoU策略）",
                        extra={
                            "text": region.text,
                            "matched_text": existing.text,
                            "iou": iou,
                            "text_sim": text_sim
                        }
                    )
                    return True, existing

            # 策略2: 检测中心点距离
            dist = self._calculate_center_distance(region.bbox, existing.bbox)
            if dist < self.distance_threshold:
                # 距离很近，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    region.text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    logger.debug(
                        "检测到重复文字（距离策略）",
                        extra={
                            "text": region.text,
                            "matched_text": existing.text,
                            "distance": dist,
                            "text_sim": text_sim
                        }
                    )
                    return True, existing

        return False, None

    def is_duplicate_by_bbox_text(
        self,
        text: str,
        bbox: BoundingBox,
        confidence: float,
        existing_regions: List[HybridTextRegion]
    ) -> Tuple[bool, Optional[HybridTextRegion]]:
        """
        通过文本和bbox检查是否重复（用于避免创建完整对象）

        Args:
            text: 文字内容
            bbox: 边界框
            confidence: 置信度
            existing_regions: 已存在的区域列表

        Returns:
            (is_duplicate, matched_region): 是否重复，匹配的已存在区域
        """
        for existing in existing_regions:
            # 策略1: 检测bbox重叠 (IoU)
            iou = self._calculate_iou(bbox, existing.bbox)
            if iou > self.iou_threshold:
                # 有重叠，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    logger.debug(
                        "检测到重复文字（IoU策略-简化版）",
                        extra={
                            "text": text,
                            "matched_text": existing.text,
                            "iou": iou,
                            "text_sim": text_sim
                        }
                    )
                    return True, existing

            # 策略2: 检测中心点距离
            dist = self._calculate_center_distance(bbox, existing.bbox)
            if dist < self.distance_threshold:
                # 距离很近，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    logger.debug(
                        "检测到重复文字（距离策略-简化版）",
                        extra={
                            "text": text,
                            "matched_text": existing.text,
                            "distance": dist,
                            "text_sim": text_sim
                        }
                    )
                    return True, existing

        return False, None

    def _calculate_iou(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """
        计算两个边界框的IoU (Intersection over Union)

        IoU = 交集面积 / 并集面积
        """
        # 计算交集区域
        x_left = max(bbox1.x, bbox2.x)
        y_top = max(bbox1.y, bbox2.y)
        x_right = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y_bottom = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # 计算并集面积
        bbox1_area = bbox1.width * bbox1.height
        bbox2_area = bbox2.width * bbox2.height
        union_area = bbox1_area + bbox2_area - intersection_area

        if union_area == 0:
            return 0.0

        return intersection_area / union_area

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算文本相似度（使用编辑距离）
        """
        try:
            import Levenshtein
            max_len = max(len(text1), len(text2))
            if max_len == 0:
                return 1.0
            distance = Levenshtein.distance(text1, text2)
            return 1.0 - (distance / max_len)
        except ImportError:
            # 如果没有Levenshtein库，使用简单相似度
            if text1 == text2:
                return 1.0
            return 0.0

    def _calculate_center_distance(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """
        计算两个边界框中心点的欧氏距离
        """
        center1_x = bbox1.x + bbox1.width / 2
        center1_y = bbox1.y + bbox1.height / 2
        center2_x = bbox2.x + bbox2.width / 2
        center2_y = bbox2.y + bbox2.height / 2

        return ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5


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

        改进的融合策略：
        1. 文字内容：以传统OCR为准
        2. 坐标位置：使用传统OCR的精确坐标
        3. 样式信息：使用多模态大模型的识别结果
        4. 数据匹配：通过文字相似度和位置距离匹配
        5. 去重检测：使用TextDeduplicator进行严格去重
        6. 不添加多模态独有结果（避免重复）

        Args:
            traditional_regions: 传统OCR识别结果
            multimodal_regions: 多模态OCR识别结果

        Returns:
            List[HybridTextRegion]: 融合后的文字区域列表
        """
        # 初始化去重器
        deduplicator = TextDeduplicator(
            iou_threshold=0.3,           # 30%重叠即认为重复
            text_similarity_threshold=0.85,  # 85%文字相似度
            distance_threshold=50.0      # 50像素距离
        )

        merged = []
        matched_multimodal_indices = set()

        # 第一阶段：遍历传统OCR结果（精确坐标为主）
        for trad_idx, trad_region in enumerate(traditional_regions):
            # 在多模态结果中找匹配
            best_match_idx, best_match_score = await self._find_best_match(
                trad_region,
                multimodal_regions,
                matched_multimodal_indices
            )

            # 使用简化的去重检测，避免创建临时对象
            is_dup, matched = deduplicator.is_duplicate_by_bbox_text(
                trad_region.text,
                trad_region.bbox,
                trad_region.confidence,
                merged
            )
            if is_dup:
                logger.debug(
                    "跳过重复的传统OCR文字",
                    extra={
                        "text": trad_region.text,
                        "matched_text": matched.text if matched else ""
                    }
                )
                continue

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

        # 第二阶段：检查多模态独有结果（默认不添加，避免重复）
        # 如需添加"补漏字"功能，应使用严格的去重检测
        multimodal_only_count = 0
        for multi_idx, multi_region in enumerate(multimodal_regions):
            if multi_idx not in matched_multimodal_indices:
                multimodal_only_count += 1

                # 使用简化的去重检测
                is_dup, matched = deduplicator.is_duplicate_by_bbox_text(
                    multi_region.text,
                    multi_region.bbox,
                    multi_region.confidence,
                    merged
                )
                if not is_dup:
                    # 只有当文字较长（非零散字符）且置信度较高时才添加
                    if len(multi_region.text.strip()) >= 2 and multi_region.confidence > 0.7:
                        merged.append(HybridTextRegion(
                            id=f"region_{len(merged) + 1:03d}",
                            text=multi_region.text,
                            bbox=multi_region.bbox,
                            confidence=multi_region.confidence * 0.85,  # 降低置信度
                            font=multi_region.font,
                            color=multi_region.font.color,
                            source="multimodal"
                        ))

        logger.info(
            "混合OCR融合完成",
            extra={
                "traditional_count": len(traditional_regions),
                "multimodal_count": len(multimodal_regions),
                "merged_count": len(merged),
                "multimodal_only_count": multimodal_only_count,
                "duplicates_removed": len(traditional_regions) + multimodal_only_count - len(merged)
            }
        )

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
