"""
大纲辅助工具
负责解析和验证AI响应的大纲内容
"""

from typing import List, Dict, Any
from app.core.log_utils import get_logger
from app.schemas.generation_outline import OutlineSlide

logger = get_logger(__name__)


class OutlineHelper:
    """大纲辅助工具"""

    def parse_ai_response(self, ai_response: str) -> str:
        """
        解析AI响应内容（markdown格式）

        Args:
            ai_response: AI响应内容

        Returns:
            str: 清理后的原始markdown内容
        """
        try:
            # 清理响应内容，移除可能的代码块标记
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```markdown'):
                cleaned_response = cleaned_response[11:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # 直接返回原始markdown内容，不进行解析
            return cleaned_response

        except Exception as e:
            logger.error(
                message="解析AI响应markdown失败",
                operation="parse_ai_response_failed",
                exception=e,
                extra_data={"response_preview": ai_response[:200]}
            )
            raise ValueError(f"AI响应格式错误: {e}")

    def validate_and_convert_outline(
        self,
        outline_data: List[Dict[str, Any]],
        expected_slide_count: int
    ) -> List[OutlineSlide]:
        """
        验证和转换大纲数据

        Args:
            outline_data: 原始大纲数据
            expected_slide_count: 期望的幻灯片数量

        Returns:
            List[OutlineSlide]: 验证后的OutlineSlide列表
        """
        if len(outline_data) != expected_slide_count:
            logger.warning(
                f"生成的幻灯片数量({len(outline_data)})与期望数量({expected_slide_count})不匹配",
                operation="slide_count_mismatch"
            )

        outline_slides = []
        for i, slide_data in enumerate(outline_data):
            try:
                # 验证必需字段
                required_fields = ['slide_index', 'title', 'points', 'slide_type', 'needs_image']
                for field in required_fields:
                    if field not in slide_data:
                        raise ValueError(f"幻灯片 {i} 缺少必需字段: {field}")

                # 创建OutlineSlide实例
                outline_slide = OutlineSlide(
                    slide_index=slide_data['slide_index'],
                    title=slide_data['title'],
                    points=slide_data['points'],
                    slide_type=slide_data['slide_type'],
                    needs_image=slide_data['needs_image']
                )

                outline_slides.append(outline_slide)

            except Exception as e:
                logger.error(
                    f"验证幻灯片数据失败: 索引 {i}",
                    operation="validate_slide_failed",
                    exception=e,
                    slide_data=slide_data
                )
                raise ValueError(f"幻灯片 {i} 数据验证失败: {e}")

        return outline_slides