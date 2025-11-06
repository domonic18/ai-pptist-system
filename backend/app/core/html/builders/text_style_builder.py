"""
文本样式构建器模块
提供文本元素特定的样式构建功能
"""

from typing import List
from app.schemas.layout_optimization import ElementData
from .base_style_builder import BaseStyleBuilder


class TextStyleBuilder(BaseStyleBuilder):
    """文本样式构建器"""

    def build_styles(self, element: ElementData) -> List[str]:
        """构建文本元素样式"""
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

        # 字体样式
        if element.defaultFontName:
            styles.append(f"font-family: '{element.defaultFontName}'")

        if element.defaultColor:
            styles.append(f'color: {element.defaultColor}')

        if element.fontSize:
            styles.append(f'font-size: {int(element.fontSize)}px')

        if element.fontWeight:
            weight = 'bold' if str(element.fontWeight).lower() in ['bold', '700'] else element.fontWeight
            styles.append(f'font-weight: {weight}')

        if element.textAlign:
            styles.append(f'text-align: {element.textAlign}')

        if element.lineHeight:
            styles.append(f'line-height: {element.lineHeight}')

        if element.wordSpace:
            styles.append(f'letter-spacing: {element.wordSpace}px')

        if element.paragraphSpace:
            styles.append(f'margin-bottom: {element.paragraphSpace}px')

        return styles