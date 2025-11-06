"""
基础样式构建器模块
提供所有元素类型通用的样式构建功能
"""

from typing import List
from app.schemas.layout_optimization import ElementData
from app.core.html.html_utils import parse_shadow_style, parse_filter_style, parse_outline_style


class BaseStyleBuilder:
    """基础样式构建器"""

    def build_position_styles(self, element: ElementData) -> List[str]:
        """构建位置相关样式"""
        return [
            'position: absolute',
            f'left: {int(element.left or 0)}px',
            f'top: {int(element.top or 0)}px',
            f'width: {int(element.width or 0)}px',
            f'height: {int(element.height or 0)}px',
            f'transform: rotate({int(element.rotate or 0)}deg)',
        ]

    def build_common_styles(self, element: ElementData) -> List[str]:
        """构建通用样式"""
        styles = []

        # 背景色
        if element.fill:
            styles.append(f'background: {element.fill}')

        # 边框轮廓
        outline_style = parse_outline_style(element.outline)
        if outline_style:
            width = outline_style.get('width', 1)
            style = outline_style.get('style', 'solid')
            color = outline_style.get('color', '#000')
            styles.append(f'border: {width}px {style} {color}')

        # 阴影
        shadow_style = parse_shadow_style(element.shadow)
        if shadow_style:
            styles.append(f'box-shadow: {shadow_style}')

        # 透明度
        if element.opacity is not None:
            styles.append(f'opacity: {element.opacity}')

        # 滤镜
        filter_style = parse_filter_style(element.filter)
        if filter_style:
            styles.append(f'filter: {filter_style}')

        return styles

    def build_flip_styles(self, element: ElementData) -> List[str]:
        """构建翻转样式"""
        styles = []
        if element.flipH:
            styles.append('scaleX(-1)')
        if element.flipV:
            styles.append('scaleY(-1)')

        if styles:
            return [f'transform: rotate({int(element.rotate or 0)}deg) {"".join(styles)}']
        return []