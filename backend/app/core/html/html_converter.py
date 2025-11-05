"""
HTML转换器模块
负责将PPTist元素转换为HTML格式，供LLM优化使用
"""

from typing import List
from app.schemas.layout_optimization import ElementData, CanvasSize
from .html_utils import (
    parse_shadow_style,
    parse_filter_style,
    parse_outline_style
)


class HTMLConverter:
    """PPTist元素到HTML的转换器"""
    
    def convert_to_html(
        self,
        elements: List[ElementData],
        canvas_size: CanvasSize
    ) -> str:
        """
        将PPTist元素列表转换为HTML格式
        
        Args:
            elements: PPTist元素列表
            canvas_size: 画布尺寸
            
        Returns:
            str: HTML字符串
        """
        html_parts = [
            f'<div class="ppt-canvas" style="width: {canvas_size.width}px; height: {canvas_size.height}px; position: relative; background: white;">\n'
        ]
        
        for el in elements:
            if el.type == 'text':
                html_parts.append(self._convert_text_element(el))
            elif el.type == 'shape':
                html_parts.append(self._convert_shape_element(el))
            elif el.type == 'image':
                html_parts.append(self._convert_image_element(el))
            elif el.type == 'line':
                html_parts.append(self._convert_line_element(el))
                
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def _convert_text_element(self, el: ElementData) -> str:
        """
        将文本元素转换为HTML

        Args:
            el: 文本元素

        Returns:
            str: HTML字符串
        """
        styles = [
            'position: absolute',
            f'left: {int(el.left)}px',
            f'top: {int(el.top)}px',
            f'width: {int(el.width or 0)}px',
            f'height: {int(el.height or 0)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]

        # 字体样式
        if el.defaultFontName:
            styles.append(f"font-family: '{el.defaultFontName}'")
        if el.defaultColor:
            styles.append(f'color: {el.defaultColor}')
        if el.lineHeight:
            styles.append(f'line-height: {el.lineHeight}')
        if el.fontSize:
            styles.append(f'font-size: {int(el.fontSize)}px')
        if el.fontWeight:
            styles.append(f'font-weight: {el.fontWeight}')
        if el.textAlign:
            styles.append(f'text-align: {el.textAlign}')
        if el.wordSpace:
            styles.append(f'letter-spacing: {el.wordSpace}px')
        if el.paragraphSpace:
            styles.append(f'margin-bottom: {el.paragraphSpace}px')

        # 处理outline（使用共享工具函数）
        outline_style = parse_outline_style(el.outline)
        if outline_style:
            width = outline_style.get('width', 1)
            style = outline_style.get('style', 'solid')
            color = outline_style.get('color', '#000')
            styles.append(f'border: {width}px {style} {color}')

        # 处理阴影（使用共享工具函数）
        shadow_css = parse_shadow_style(el.shadow)
        if shadow_css:
            styles.append(f'box-shadow: {shadow_css}')

        # 处理透明度
        if el.opacity is not None:
            styles.append(f'opacity: {el.opacity}')

        # 处理翻转
        flip_transforms = []
        if el.flipH:
            flip_transforms.append('scaleX(-1)')
        if el.flipV:
            flip_transforms.append('scaleY(-1)')

        if flip_transforms:
            # 将翻转变换添加到现有的transform中
            existing_transform = f'transform: rotate({int(el.rotate)}deg)'
            if existing_transform in styles:
                styles.remove(existing_transform)
            full_transform = f'transform: rotate({int(el.rotate)}deg) {" ".join(flip_transforms)}'
            styles.append(full_transform)

        # 处理填充背景
        if el.fill:
            styles.append(f'background: {el.fill}')

        style_str = '; '.join(styles)
        content = el.content or ''

        return f'''  <div
    class="ppt-element ppt-text"
    data-id="{el.id}"
    data-type="text"
    style="{style_str}">
    {content}
  </div>\n'''
    
    def _convert_shape_element(self, el: ElementData) -> str:
        """
        将形状元素转换为HTML

        Args:
            el: 形状元素

        Returns:
            str: HTML字符串
        """
        styles = [
            'position: absolute',
            f'left: {int(el.left)}px',
            f'top: {int(el.top)}px',
            f'width: {int(el.width or 0)}px',
            f'height: {int(el.height or 0)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]

        # 处理填充颜色（包括渐变）
        if el.fill:
            styles.append(f'background: {el.fill}')

        # 添加圆角半径（如果存在）
        if el.radius:
            styles.append(f'border-radius: {int(el.radius)}px')

        # 处理outline（使用共享工具函数）
        outline_style = parse_outline_style(el.outline)
        if outline_style:
            width = outline_style.get('width', 1)
            style = outline_style.get('style', 'solid')
            color = outline_style.get('color', '#000')
            styles.append(f'border: {width}px {style} {color}')

        # 处理阴影（使用共享工具函数）
        shadow_css = parse_shadow_style(el.shadow)
        if shadow_css:
            styles.append(f'box-shadow: {shadow_css}')

        # 处理透明度
        if el.opacity is not None:
            styles.append(f'opacity: {el.opacity}')

        # 处理翻转
        flip_transforms = []
        if el.flipH:
            flip_transforms.append('scaleX(-1)')
        if el.flipV:
            flip_transforms.append('scaleY(-1)')

        if flip_transforms:
            # 将翻转变换添加到现有的transform中
            existing_transform = f'transform: rotate({int(el.rotate)}deg)'
            if existing_transform in styles:
                styles.remove(existing_transform)
            full_transform = f'transform: rotate({int(el.rotate)}deg) {" ".join(flip_transforms)}'
            styles.append(full_transform)

        style_str = '; '.join(styles)

        # 处理形状文字内容（text字段是字典）
        text_content = ''
        if el.text and isinstance(el.text, dict):
            text_content = el.text.get('content', '')
        elif el.text:
            text_content = str(el.text)

        return f'''  <div
    class="ppt-element ppt-shape"
    data-id="{el.id}"
    data-type="shape"
    style="{style_str}">
    <div class="shape-text">
      {text_content}
    </div>
  </div>\n'''
    
    def _convert_image_element(self, el: ElementData) -> str:
        """
        将图片元素转换为HTML

        Args:
            el: 图片元素

        Returns:
            str: HTML字符串
        """
        styles = [
            'position: absolute',
            f'left: {int(el.left)}px',
            f'top: {int(el.top)}px',
            f'width: {int(el.width or 0)}px',
            f'height: {int(el.height or 0)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]

        # 添加圆角半径（如果存在）
        if el.radius:
            styles.append(f'border-radius: {int(el.radius)}px')

        # 处理outline（使用共享工具函数）
        outline_style = parse_outline_style(el.outline)
        if outline_style:
            width = outline_style.get('width', 1)
            style = outline_style.get('style', 'solid')
            color = outline_style.get('color', '#000')
            styles.append(f'border: {width}px {style} {color}')

        # 处理阴影（使用共享工具函数）
        shadow_css = parse_shadow_style(el.shadow)
        if shadow_css:
            styles.append(f'box-shadow: {shadow_css}')

        # 处理透明度
        if el.opacity is not None:
            styles.append(f'opacity: {el.opacity}')

        # 处理翻转
        flip_transforms = []
        if el.flipH:
            flip_transforms.append('scaleX(-1)')
        if el.flipV:
            flip_transforms.append('scaleY(-1)')

        if flip_transforms:
            # 将翻转变换添加到现有的transform中
            existing_transform = f'transform: rotate({int(el.rotate)}deg)'
            if existing_transform in styles:
                styles.remove(existing_transform)
            full_transform = f'transform: rotate({int(el.rotate)}deg) {" ".join(flip_transforms)}'
            styles.append(full_transform)

        # 处理滤镜（使用共享工具函数）
        filter_css = parse_filter_style(el.filter)
        if filter_css:
            styles.append(f'filter: {filter_css}')

        style_str = '; '.join(styles)
        src = el.src or ''

        return f'''  <div
    class="ppt-element ppt-image"
    data-id="{el.id}"
    data-type="image"
    style="{style_str}">
    <img src="{src}" style="width: 100%; height: 100%; object-fit: contain;" />
  </div>\n'''
    
    def _convert_line_element(self, el: ElementData) -> str:
        """
        将线条元素转换为HTML

        Args:
            el: 线条元素

        Returns:
            str: HTML字符串
        """
        styles = [
            'position: absolute',
            f'left: {int(el.left)}px',
            f'top: {int(el.top)}px',
            f'width: {int(el.width or 0)}px',
            f'height: {int(el.height or 0)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]

        # 添加线条样式
        if el.fill:
            styles.append(f'background-color: {el.fill}')
        else:
            styles.append('background-color: #000000')  # 默认黑色线条

        # 处理outline（使用共享工具函数）
        outline_style = parse_outline_style(el.outline)
        if outline_style:
            width = outline_style.get('width', 1)
            style = outline_style.get('style', 'solid')
            color = outline_style.get('color', '#000')
            styles.append(f'border: {width}px {style} {color}')

        # 处理阴影（使用共享工具函数）
        shadow_css = parse_shadow_style(el.shadow)
        if shadow_css:
            styles.append(f'box-shadow: {shadow_css}')

        # 处理透明度
        if el.opacity is not None:
            styles.append(f'opacity: {el.opacity}')

        # 处理翻转
        flip_transforms = []
        if el.flipH:
            flip_transforms.append('scaleX(-1)')
        if el.flipV:
            flip_transforms.append('scaleY(-1)')

        if flip_transforms:
            # 将翻转变换添加到现有的transform中
            existing_transform = f'transform: rotate({int(el.rotate)}deg)'
            if existing_transform in styles:
                styles.remove(existing_transform)
            full_transform = f'transform: rotate({int(el.rotate)}deg) {" ".join(flip_transforms)}'
            styles.append(full_transform)

        style_str = '; '.join(styles)

        return f'''  <div
    class="ppt-element ppt-line"
    data-id="{el.id}"
    data-type="line"
    style="{style_str}">
  </div>\n'''

