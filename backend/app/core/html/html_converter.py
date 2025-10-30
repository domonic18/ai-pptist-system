"""
HTML转换器模块
负责将PPTist元素转换为HTML格式，供LLM优化使用
"""

from typing import List
from app.schemas.layout_optimization import ElementData, CanvasSize


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
            f'width: {int(el.width)}px',
            f'height: {int(el.height)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]
        
        if el.defaultFontName:
            styles.append(f"font-family: '{el.defaultFontName}'")
        if el.defaultColor:
            styles.append(f'color: {el.defaultColor}')
        if el.lineHeight:
            styles.append(f'line-height: {el.lineHeight}')
            
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
            f'width: {int(el.width)}px',
            f'height: {int(el.height)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]
        
        if el.fill:
            styles.append(f'background-color: {el.fill}')
            
        # 处理outline（可能是字符串或字典）
        if el.outline:
            if isinstance(el.outline, dict):
                color = el.outline.get('color', '#000')
                width = el.outline.get('width', 1)
                styles.append(f'border: {width}px solid {color}')
            else:
                styles.append(f'border: 1px solid {el.outline}')
                
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
    <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
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
            f'width: {int(el.width)}px',
            f'height: {int(el.height)}px',
            f'transform: rotate({int(el.rotate)}deg)',
        ]
        
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
        线条元素暂不优化，返回占位div
        
        Args:
            el: 线条元素
            
        Returns:
            str: HTML字符串
        """
        styles = [
            'position: absolute',
            f'left: {int(el.left)}px',
            f'top: {int(el.top)}px',
            'width: 1px',
            'height: 1px',
            'background: transparent',
        ]
        
        style_str = '; '.join(styles)
        
        return f'''  <div
    class="ppt-element ppt-line"
    data-id="{el.id}"
    data-type="line"
    style="{style_str}">
    <!-- 线条元素暂不优化 -->
  </div>\n'''

