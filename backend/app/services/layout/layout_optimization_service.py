"""
布局优化Service（核心业务逻辑）
负责数据转换、LLM调用、结果解析、数据验证
"""

from typing import List, Optional, Dict, Any
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from bs4 import BeautifulSoup

from app.schemas.layout_optimization import (
    ElementData,
    CanvasSize,
    OptimizationOptions
)
from app.core.llm.client import AIClient
from app.core.log_utils import get_logger
from app.prompts import get_prompt_manager
from app.prompts.utils import PromptHelper

logger = get_logger(__name__)


class LayoutOptimizationService:
    """布局优化服务（核心业务逻辑）"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_client = AIClient()
        self.prompt_manager = get_prompt_manager()
        self.prompt_helper = PromptHelper(self.prompt_manager)

    async def optimize_layout(
        self,
        slide_id: str,
        elements: List[ElementData],
        canvas_size: CanvasSize,
        options: Optional[OptimizationOptions] = None
    ) -> List[ElementData]:
        """
        优化幻灯片布局的核心方法

        Args:
            slide_id: 幻灯片ID
            elements: 元素列表
            canvas_size: 画布尺寸
            options: 优化选项

        Returns:
            List[ElementData]: 优化后的元素列表

        Raises:
            ValueError: 验证失败
            Exception: 其他异常
        """
        logger.info(
            "开始执行布局优化",
            operation="optimize_layout",
            slide_id=slide_id,
            elements_count=len(elements)
        )

        try:
            # 1. 转换PPTist元素为HTML
            html_content = self._convert_to_html(
                elements, canvas_size
            )
            logger.info(
                "PPTist元素已转换为HTML",
                operation="convert_to_html",
                html_length=len(html_content)
            )

            # 2. 构建提示词参数
            requirements = self._build_requirements(options)
            user_prompt_params = {
                "canvas_width": canvas_size.width,
                "canvas_height": canvas_size.height,
                "html_content": html_content,
                "requirements": requirements
            }

            # 3. 准备提示词
            system_prompt, user_prompt, temperature, max_tokens = \
                self.prompt_helper.prepare_prompts(
                    category="presentation",
                    template_name="layout_optimization",
                    user_prompt_params=user_prompt_params
                )

            # 4. 调用LLM（使用现有AIClient）
            logger.info(
                "调用LLM进行HTML布局优化",
                operation="optimize_layout_llm_call",
                slide_id=slide_id
            )

            llm_response = await self.ai_client.ai_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            logger.info(
                "LLM HTML响应接收完成",
                operation="optimize_layout_llm_response",
                response_length=len(llm_response)
            )

            # 5. 解析HTML响应，提取纯HTML内容
            optimized_html = self._extract_html_from_response(llm_response)

            # 6. 解析HTML DOM，转换为PPTist元素
            optimized_elements = self._parse_html_to_elements(
                optimized_html, elements
            )

            # 7. 验证结果（确保内容不变、ID一致等）
            self._validate_optimized_elements(optimized_elements, elements)

            logger.info(
                "布局优化执行成功",
                operation="optimize_layout_success",
                slide_id=slide_id,
                optimized_count=len(optimized_elements)
            )

            return optimized_elements

        except Exception as e:
            logger.error(
                "布局优化执行失败",
                operation="optimize_layout_failed",
                slide_id=slide_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _convert_to_html(
        self,
        elements: List[ElementData],
        canvas_size: CanvasSize
    ) -> str:
        """
        将PPTist元素转换为HTML格式
        利用LLM擅长HTML的特性
        """
        html_parts = [
            f'<div class="ppt-canvas" style="width: {canvas_size.width}px; height: {canvas_size.height}px; position: relative; background: white;">\n'
        ]

        for el in elements:
            if el.type == 'text':
                html_parts.append(self._element_to_html_text(el))
            elif el.type == 'shape':
                html_parts.append(self._element_to_html_shape(el))
            elif el.type == 'image':
                html_parts.append(self._element_to_html_image(el))
            elif el.type == 'line':
                # 线条元素暂不优化，保持原样
                html_parts.append(self._element_to_html_line(el))

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _element_to_html_text(self, el: ElementData) -> str:
        """文本元素转HTML"""
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

    def _element_to_html_shape(self, el: ElementData) -> str:
        """形状元素转HTML"""
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

        # 形状内部文字使用单独的div
        return f'''  <div
    class="ppt-element ppt-shape"
    data-id="{el.id}"
    data-type="shape"
    style="{style_str}">
    <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
      {text_content}
    </div>
  </div>\n'''

    def _element_to_html_line(self, el: ElementData) -> str:
        """线条元素转HTML"""
        # 线条元素暂不优化，返回一个占位div保持位置
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

    def _build_requirements(self, options: Optional[OptimizationOptions]) -> str:
        """构建优化要求文本"""
        requirements = []

        if options:
            if options.keep_colors:
                requirements.append("- 保持原有颜色方案，不得更改元素颜色")
            if options.keep_fonts:
                requirements.append("- 保持原有字体，不得更改font-family")

            style_hints = {
                'professional': '专业、商务、简洁',
                'creative': '创意、活泼、大胆',
                'minimal': '极简、留白、克制'
            }
            style = options.style or 'professional'
            requirements.append(f"- 优化风格：{style_hints.get(style, '专业')}")
        else:
            requirements.append("- 全面优化布局、字体大小、颜色、间距")

        return "\n".join(requirements) if requirements else "全面优化"

    def _extract_html_from_response(self, llm_response: str) -> str:
        """
        从LLM响应中提取纯HTML内容
        LLM可能返回markdown格式或带注释的内容
        """
        # 移除markdown代码块标记
        html = llm_response.strip()

        # 如果包含```html，提取其中的内容
        if '```html' in html:
            html = re.search(r'```html\s*(.*?)\s*```', html, re.DOTALL)
            if html:
                html = html.group(1)
        elif '```' in html:
            html = re.search(r'```\s*(.*?)\s*```', html, re.DOTALL)
            if html:
                html = html.group(1)

        # 提取<div class="ppt-canvas">...</div>
        match = re.search(
            r'<div\s+class="ppt-canvas".*?</div>\s*$',
            html,
            re.DOTALL | re.MULTILINE
        )

        if not match:
            raise ValueError("LLM响应中未找到有效的HTML结构")

        return match.group(0)

    def _parse_html_to_elements(
        self,
        html_content: str,
        original_elements: List[ElementData]
    ) -> List[ElementData]:
        """
        解析HTML DOM，转换为PPTist元素列表

        Args:
            html_content: 优化后的HTML
            original_elements: 原始元素列表（用于保留未优化的字段）

        Returns:
            List[ElementData]: 优化后的元素列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 构建原始元素ID映射
        original_map = {el.id: el for el in original_elements}

        # 查找所有PPT元素
        ppt_elements = soup.find_all(class_='ppt-element')

        optimized_elements = []

        for elem in ppt_elements:
            # 获取data-id和data-type
            element_id = elem.get('data-id')
            element_type = elem.get('data-type')

            if not element_id or not element_type:
                continue

            # 获取原始元素
            original = original_map.get(element_id)
            if not original:
                logger.warning(f"未找到原始元素: {element_id}")
                continue

            # 解析样式
            style_dict = self._parse_inline_style(elem.get('style', ''))

            # 根据类型解析
            if element_type == 'text':
                optimized = self._parse_html_text_element(elem, style_dict, original)
            elif element_type == 'shape':
                optimized = self._parse_html_shape_element(elem, style_dict, original)
            elif element_type == 'image':
                optimized = self._parse_html_image_element(elem, style_dict, original)
            elif element_type == 'line':
                # 线条元素保持原样
                optimized = original
            else:
                continue

            optimized_elements.append(optimized)

        return optimized_elements

    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """
        解析内联样式字符串为字典

        Input: "position: absolute; left: 100px; top: 50px; color: #333"
        Output: {"position": "absolute", "left": "100px", "top": "50px", "color": "#333"}
        """
        style_dict = {}
        if not style_str:
            return style_dict

        for item in style_str.split(';'):
            item = item.strip()
            if ':' in item:
                key, value = item.split(':', 1)
                style_dict[key.strip()] = value.strip()

        return style_dict

    def _parse_px_value(self, value: str) -> float:
        """
        解析px值

        Input: "100px" or "100"
        Output: 100.0
        """
        if not value:
            return 0.0

        value = str(value).strip()
        if value.endswith('px'):
            value = value[:-2]

        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _parse_rotate_value(self, transform: str) -> float:
        """
        从transform中解析旋转角度

        Input: "rotate(15deg)"
        Output: 15.0
        """
        if not transform:
            return 0.0

        match = re.search(r'rotate\s*\(\s*([-\d.]+)deg\s*\)', transform)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                pass

        return 0.0

    def _parse_html_text_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML文本元素为PPTist文本元素
        """
        # 提取文本内容
        text_content = elem.get_text(strip=True)

        # 构建优化后的元素
        optimized = ElementData(
            id=elem.get('data-id'),
            type='text',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', 0)),
            top=self._parse_px_value(style_dict.get('top', 0)),
            width=self._parse_px_value(style_dict.get('width', original.width)),
            height=self._parse_px_value(style_dict.get('height', original.height)),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 文本内容（必须与原始一致）
            content=text_content,
            # 字体样式
            defaultFontName=style_dict.get('font-family', original.defaultFontName or '').strip("'\""),
            defaultColor=style_dict.get('color', original.defaultColor),
            lineHeight=float(style_dict.get('line-height', original.lineHeight or 1.5)),
        )

        # 可选字段
        if 'font-size' in style_dict:
            optimized.fontSize = self._parse_px_value(style_dict['font-size'])
        if 'font-weight' in style_dict:
            optimized.fontWeight = style_dict['font-weight']
        if 'text-align' in style_dict:
            optimized.textAlign = style_dict['text-align']

        return optimized

    def _parse_html_shape_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML形状元素为PPTist形状元素
        """
        # 提取形状内部文字
        shape_text_elem = elem.find(class_='shape-text')
        text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''

        # 解析border
        outline = None
        if 'border' in style_dict:
            border_match = re.match(r'(\d+)px\s+solid\s+(#[0-9a-fA-F]{3,6})', style_dict['border'])
            if border_match:
                outline = {
                    'width': int(border_match.group(1)),
                    'color': border_match.group(2)
                }

        optimized = ElementData(
            id=elem.get('data-id'),
            type='shape',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', 0)),
            top=self._parse_px_value(style_dict.get('top', 0)),
            width=self._parse_px_value(style_dict.get('width', original.width)),
            height=self._parse_px_value(style_dict.get('height', original.height)),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 形状样式
            fill=style_dict.get('background-color', original.fill),
            outline=outline or original.outline,
            text=text_content,
        )

        # 可选：圆角
        if 'border-radius' in style_dict:
            optimized.borderRadius = self._parse_px_value(style_dict['border-radius'])

        return optimized

    def _parse_html_image_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML图片元素为PPTist图片元素
        """
        optimized = ElementData(
            id=elem.get('data-id'),
            type='image',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', 0)),
            top=self._parse_px_value(style_dict.get('top', 0)),
            width=self._parse_px_value(style_dict.get('width', original.width)),
            height=self._parse_px_value(style_dict.get('height', original.height)),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 图片源
            src=elem.get('src', original.src),
            fixedRatio=original.fixedRatio,
        )

        # 可选：圆角
        if 'border-radius' in style_dict:
            optimized.borderRadius = self._parse_px_value(style_dict['border-radius'])

        return optimized

    def _validate_optimized_elements(
        self,
        optimized: List[ElementData],
        original: List[ElementData]
    ):
        """验证优化结果（确保内容不变、ID一致）"""
        # 1. 元素数量应该一致
        if len(optimized) != len(original):
            raise ValueError(
                f"优化后元素数量({len(optimized)})与原始数量({len(original)})不匹配"
            )

        # 2. 所有元素ID应该保持一致
        original_ids = {el.id for el in original}
        optimized_ids = {el.id for el in optimized}

        if original_ids != optimized_ids:
            missing = original_ids - optimized_ids
            extra = optimized_ids - original_ids
            raise ValueError(
                f"元素ID不匹配：缺失{missing}，多余{extra}"
            )

        # 3. 验证文本内容未被修改
        for orig_el in original:
            if orig_el.type == "text" and orig_el.content:
                opt_el = next((el for el in optimized if el.id == orig_el.id), None)
                if opt_el and opt_el.content != orig_el.content:
                    logger.warning(
                        "文本内容被修改，已恢复原始内容",
                        element_id=orig_el.id
                    )
                    # 强制恢复原始内容
                    opt_el.content = orig_el.content