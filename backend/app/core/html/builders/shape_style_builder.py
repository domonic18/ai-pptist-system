"""
形状样式构建器模块
提供形状元素特定的样式构建功能
"""

from typing import List
from app.schemas.layout_optimization import ElementData
from .base_style_builder import BaseStyleBuilder


class ShapeStyleBuilder(BaseStyleBuilder):
    """形状样式构建器"""

    def build_styles(self, element: ElementData) -> List[str]:
        """构建形状元素样式"""
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

        # 圆角
        if element.radius is not None:
            styles.append(f'border-radius: {int(element.radius)}px')

        return styles