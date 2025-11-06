"""
线条样式构建器模块
提供线条元素特定的样式构建功能
"""

from typing import List
from app.schemas.layout_optimization import ElementData
from .base_style_builder import BaseStyleBuilder


class LineStyleBuilder(BaseStyleBuilder):
    """线条样式构建器"""

    def build_styles(self, element: ElementData) -> List[str]:
        """构建线条元素样式"""
        styles = []

        # 基础位置样式
        styles.extend(self.build_position_styles(element))

        # 通用样式
        styles.extend(self.build_common_styles(element))

        # 翻转样式
        flip_styles = self.build_flip_styles(element)
        if flip_styles:
            # 移除重复的transform
            styles = [s for s in styles if not s.startswith('transform:')]
            styles.extend(flip_styles)

        # 线条特定样式 - 如果没有设置背景色，使用默认颜色
        if not element.fill:
            styles.append('background: #000000')

        return styles