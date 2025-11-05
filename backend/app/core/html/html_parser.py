"""
HTML解析器模块
负责解析LLM返回的HTML，转换回PPTist元素格式
"""

from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup

from app.schemas.layout_optimization import ElementData
from app.core.log_utils import get_logger
from .html_utils import (
    parse_inline_style,
    parse_px_value,
    parse_rotate_value,
    parse_radius_value
)

logger = get_logger(__name__)


class HTMLParser:
    """HTML到PPTist元素的解析器"""
    
    def extract_html_from_response(self, llm_response: str) -> str:
        """
        从LLM响应中提取纯HTML内容

        Args:
            llm_response: LLM的原始响应

        Returns:
            str: 提取的HTML内容

        Raises:
            ValueError: 如果无法提取有效HTML
        """
        if not llm_response or not llm_response.strip():
            raise ValueError("LLM响应为空")

        html = llm_response.strip()

        logger.debug(
            "开始提取HTML",
            operation="extract_html_start",
            response_length=len(html),
            response_preview=html[:200] if html else ""
        )

        # 1. 如果包含markdown代码块，提取代码块内容
        if '```html' in html:
            match = re.search(r'```html\s*(.*?)\s*```', html, re.DOTALL)
            if match:
                html = match.group(1).strip()
                logger.debug(
                    "提取HTML代码块",
                    operation="extract_html_codeblock",
                    extracted_length=len(html)
                )
        elif '```' in html:
            match = re.search(r'```\s*(.*?)\s*```', html, re.DOTALL)
            if match:
                html = match.group(1).strip()
                logger.debug(
                    "提取通用代码块",
                    operation="extract_generic_codeblock",
                    extracted_length=len(html)
                )

        # 2. 验证HTML是否包含ppt-canvas
        if '<div class="ppt-canvas"' not in html and '<div class=\'ppt-canvas\'' not in html:
            logger.error(
                "未找到ppt-canvas元素",
                operation="missing_ppt_canvas",
                html_preview=html[:500] if html else ""
            )
            raise ValueError("LLM响应中未找到ppt-canvas元素")

        # 3. 使用BeautifulSoup验证HTML结构完整性
        try:
            soup = BeautifulSoup(html, 'html.parser')
            canvas = soup.find('div', class_='ppt-canvas')

            if not canvas:
                logger.error(
                    "无法解析ppt-canvas元素",
                    operation="parse_ppt_canvas_failed",
                    html_preview=html[:500] if html else ""
                )
                raise ValueError("无法解析ppt-canvas元素")

            # 返回完整的canvas HTML（包括所有子元素）
            result = str(canvas)

            logger.debug(
                "HTML提取成功",
                operation="extract_html_success",
                result_length=len(result),
                result_preview=result[:200] if result else ""
            )

            return result

        except Exception as e:
            logger.error(
                "HTML解析异常",
                operation="html_parse_exception",
                error=str(e),
                error_type=type(e).__name__,
                html_preview=html[:500] if html else ""
            )
            raise ValueError(f"HTML解析失败: {str(e)}")
    
    def parse_html_to_elements(
        self,
        html_content: str,
        original_elements: List[ElementData]
    ) -> List[ElementData]:
        """
        解析HTML内容，转换为PPTist元素列表

        Args:
            html_content: HTML内容
            original_elements: 原始元素列表（用于保留未优化的字段）

        Returns:
            List[ElementData]: 解析后的元素列表

        Raises:
            ValueError: 如果解析失败
        """
        if not html_content or not html_content.strip():
            logger.error(
                "HTML内容为空",
                operation="parse_html_empty_content"
            )
            raise ValueError("HTML内容为空")

        if not original_elements:
            logger.error(
                "原始元素列表为空",
                operation="parse_html_empty_original"
            )
            raise ValueError("原始元素列表为空")

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 调试日志
            logger.debug(
                "HTML内容预览",
                operation="html_content_preview",
                html_length=len(html_content),
                html_preview=html_content[:500] if html_content else ""
            )

            # 构建原始元素ID映射
            original_map = {el.id: el for el in original_elements}

            # 查找所有PPT元素 - 使用多种选择器策略
            ppt_elements = self._find_ppt_elements(soup)

            logger.info(
                "HTML解析开始",
                operation="parse_html_start",
                html_length=len(html_content),
                found_elements_count=len(ppt_elements),
                original_elements_count=len(original_elements)
            )

            optimized_elements = []

            # 用于生成新元素的ID计数器
            next_new_id_counter = 1000

            for elem in ppt_elements:
                element_id = elem.get('data-id')
                element_type = elem.get('data-type')

                logger.debug(
                    "解析HTML元素",
                    operation="parse_html_element",
                    element_id=element_id,
                    element_type=element_type
                )

                # 处理新元素（没有data-id或data-type的元素）
                original = None

                if not element_id or not element_type:
                    # 这是LLM创建的新元素，尝试自动识别类型
                    element_class = elem.get('class', [])
                    if isinstance(element_class, list):
                        element_class = ' '.join(element_class)

                    # 根据class名称推断元素类型
                    if 'shape' in element_class or 'background' in elem.get('style', ''):
                        element_type = 'shape'
                    elif 'text' in element_class or elem.get_text(strip=True):
                        element_type = 'text'
                    elif 'image' in element_class:
                        element_type = 'image'
                    else:
                        element_type = 'shape'  # 默认为形状

                    # 生成新的element_id
                    if not element_id:
                        element_id = f"generated_{next_new_id_counter}"
                        next_new_id_counter += 1

                    logger.info(
                        "发现新元素，自动生成ID和类型",
                        operation="auto_generate_element",
                        generated_id=element_id,
                        inferred_type=element_type,
                        element_class=element_class
                    )
                else:
                    # 获取原始元素
                    original = original_map.get(element_id)
                    if not original:
                        logger.warning(
                            "未找到原始元素，但保留为新生成的装饰元素",
                            operation="treat_as_new_element",
                            element_id=element_id
                        )

                # 解析样式
                style_dict = self._parse_inline_style(elem.get('style', ''))

                # 根据类型解析元素
                try:
                    if element_type == 'text':
                        if original:
                            optimized = self._parse_text_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_text_element(elem, style_dict, element_id)
                    elif element_type == 'shape':
                        if original:
                            optimized = self._parse_shape_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_shape_element(elem, style_dict, element_id)
                    elif element_type == 'image':
                        if original:
                            optimized = self._parse_image_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_image_element(elem, style_dict, element_id)
                    elif element_type == 'line':
                        # 线条元素保持原样
                        optimized = original
                    else:
                        logger.warning(
                            "跳过未知类型元素",
                            operation="skip_unknown_type",
                            element_id=element_id,
                            element_type=element_type
                        )
                        continue

                    optimized_elements.append(optimized)

                except Exception as e:
                    import traceback
                    logger.error(
                        "元素解析失败",
                        operation="parse_element_error",
                        element_id=element_id,
                        element_type=element_type,
                        error=str(e),
                        traceback=traceback.format_exc()
                    )
                    # 解析失败时，如果是新元素则跳过，否则使用原始元素
                    if original:
                        optimized_elements.append(original)

            # 验证结果：确保至少有一些元素被优化
            if len(optimized_elements) == 0:
                logger.warning(
                    "未找到任何可优化的元素",
                    operation="no_optimized_elements",
                    html_content_length=len(html_content),
                    original_elements_count=len(original_elements)
                )
                # 返回原始元素作为回退
                return original_elements

            logger.info(
                "HTML解析完成",
                operation="parse_html_complete",
                optimized_elements_count=len(optimized_elements),
                found_element_ids=[el.id for el in optimized_elements]
            )

            return optimized_elements

        except Exception as e:
            logger.error(
                "HTML解析整体失败",
                operation="parse_html_overall_failed",
                error=str(e),
                error_type=type(e).__name__,
                html_content_length=len(html_content) if html_content else 0
            )
            # 解析失败时返回原始元素
            return original_elements
    
    def _find_ppt_elements(self, soup: BeautifulSoup) -> List:
        """
        查找所有PPT元素，包括LLM创建的新元素

        Args:
            soup: BeautifulSoup对象

        Returns:
            List: 找到的元素列表
        """
        # 方法1：通过class查找（原始元素）
        ppt_elements = soup.find_all(class_='ppt-element')

        # 方法2：查找所有直接在ppt-canvas下的div（包括新元素）
        canvas = soup.find('div', class_='ppt-canvas')
        if canvas:
            canvas_divs = canvas.find_all('div', recursive=False)
            # 添加这些div（可能包含装饰性元素）
            ppt_elements.extend(canvas_divs)

        if ppt_elements:
            logger.debug(
                "使用主选择器查找元素",
                operation="primary_element_search",
                found_count=len(ppt_elements)
            )
            return ppt_elements

        # 方法3：通过包含data-id属性的div查找
        ppt_elements = soup.find_all('div', attrs={'data-id': True})

        if ppt_elements:
            logger.info(
                "使用备用选择器查找元素",
                operation="fallback_element_search",
                found_count=len(ppt_elements)
            )
            return ppt_elements

        # 方法4：查找ppt-canvas下的所有div（包括装饰元素）
        if canvas:
            all_canvas_divs = canvas.find_all('div')
            logger.info(
                "查找canvas下所有div",
                operation="find_all_canvas_divs",
                found_count=len(all_canvas_divs)
            )
            return all_canvas_divs

        # 最后回退：查找所有div
        all_divs = soup.find_all('div')
        logger.info(
            "查找所有div",
            operation="find_all_divs",
            found_count=len(all_divs)
        )

        return all_divs
    
    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """
        解析内联样式字符串为字典

        Args:
            style_str: 样式字符串，如 "position: absolute; left: 100px"

        Returns:
            Dict[str, str]: 样式字典
        """
        return parse_inline_style(style_str)
    
    def _parse_px_value(self, value: str, default: float = 0.0) -> float:
        """
        解析px值，支持auto等特殊值

        Args:
            value: 如 "100px" 或 "100" 或 "auto"
            default: 当无法解析时返回的默认值

        Returns:
            float: 数值
        """
        return parse_px_value(value, default)
    
    def _parse_rotate_value(self, transform: str) -> float:
        """
        从transform中解析旋转角度

        Args:
            transform: 如 "rotate(15deg)"

        Returns:
            float: 角度值
        """
        return parse_rotate_value(transform)

    def _parse_radius_value(self, radius_str: str) -> Optional[float]:
        """
        解析border-radius值

        Args:
            radius_str: CSS border-radius值，如 "10px" 或 "10px 20px"

        Returns:
            Optional[float]: 圆角半径值，如果无法解析则返回None
        """
        return parse_radius_value(radius_str)
    
    def _parse_text_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML文本元素
        
        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            original: 原始元素
            
        Returns:
            ElementData: 解析后的文本元素
        """
        # 提取文本内容
        text_content = elem.get_text(strip=True)
        
        # 构建优化后的元素
        optimized = ElementData(
            id=elem.get('data-id'),
            type='text',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=self._parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=self._parse_px_value(style_dict.get('width', ''), default=original.width),
            height=self._parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 文本内容（必须与原始一致）
            content=text_content,
            # 字体样式
            defaultFontName=style_dict.get('font-family', original.defaultFontName or '').strip("'\""),
            defaultColor=style_dict.get('color', original.defaultColor),
            lineHeight=float(self._parse_px_value(style_dict.get('line-height', ''), default=original.lineHeight or 1.5)),
        )
        
        # 可选字段
        if 'font-size' in style_dict:
            optimized.fontSize = self._parse_px_value(style_dict['font-size'])
        if 'font-weight' in style_dict:
            optimized.fontWeight = style_dict['font-weight']
        if 'text-align' in style_dict:
            optimized.textAlign = style_dict['text-align']
        
        return optimized
    
    def _parse_shape_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML形状元素
        
        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            original: 原始元素
            
        Returns:
            ElementData: 解析后的形状元素
        """
        # 提取形状内部文字
        shape_text_elem = elem.find(class_='shape-text')
        text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''
        
        # 解析border
        outline = None
        if 'border' in style_dict:
            border_match = re.match(
                r'(\d+)px\s+solid\s+(#[0-9a-fA-F]{3,6})',
                style_dict['border']
            )
            if border_match:
                outline = {
                    'width': int(border_match.group(1)),
                    'color': border_match.group(2)
                }
        
        # 构建text字段（应该是字典格式）
        text_dict = {"content": text_content} if text_content else {"content": ""}
        
        # 处理background-color或background（可能包含gradient）
        fill_value = original.fill
        if 'background-color' in style_dict:
            fill_value = style_dict['background-color']
        elif 'background' in style_dict:
            bg = style_dict['background']
            # 如果是gradient，保留原始颜色
            if 'gradient' not in bg.lower():
                fill_value = bg
        
        optimized = ElementData(
            id=elem.get('data-id'),
            type='shape',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=self._parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=self._parse_px_value(style_dict.get('width', ''), default=original.width),
            height=self._parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 形状样式
            fill=fill_value,
            outline=outline or original.outline,
            text=text_dict,
        )
        
        # 注意：border-radius等样式属性在PPTist元素中可能不支持
        # 这些样式由LLM优化，但在转换回PPTist元素时会被忽略
        
        return optimized

    def _parse_new_text_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """
        解析新创建的文本元素

        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            element_id: 元素ID

        Returns:
            ElementData: 解析后的文本元素
        """
        # 提取文本内容
        text_content = elem.get_text(strip=True)

        # 构建新元素
        optimized = ElementData(
            id=element_id,
            type='text',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '100')),
            top=self._parse_px_value(style_dict.get('top', '100')),
            width=self._parse_px_value(style_dict.get('width', '200')),
            height=self._parse_px_value(style_dict.get('height', '50')),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 文本内容
            content=text_content or '新文本',
            # 默认字体样式
            defaultFontName='Arial',
            defaultColor=style_dict.get('color', '#333333'),
            lineHeight=1.5,
            fontSize=self._parse_px_value(style_dict.get('font-size', '16')),
            fontWeight=style_dict.get('font-weight', 'normal'),
            textAlign=style_dict.get('text-align', 'left'),
        )

        return optimized

    def _parse_new_shape_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """
        解析新创建的形状元素

        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            element_id: 元素ID

        Returns:
            ElementData: 解析后的形状元素
        """
        # 提取形状内部文字
        shape_text_elem = elem.find(class_='shape-text')
        text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''

        # 处理背景颜色或渐变
        fill_value = style_dict.get('background-color', '#ffffff')
        if 'background' in style_dict:
            bg = style_dict['background']
            # 如果是gradient，使用第一个颜色
            if 'gradient' in bg.lower():
                # 提取gradient中的第一个颜色
                import re
                color_match = re.search(r'#[0-9a-fA-F]{6}', bg)
                if color_match:
                    fill_value = color_match.group(0)
                else:
                    fill_value = '#47acc5'  # 默认主题色
            else:
                fill_value = bg

        optimized = ElementData(
            id=element_id,
            type='shape',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '100')),
            top=self._parse_px_value(style_dict.get('top', '100')),
            width=self._parse_px_value(style_dict.get('width', '100')),
            height=self._parse_px_value(style_dict.get('height', '100')),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 形状样式
            fill=fill_value,
            outline=None,
            text={"content": text_content} if text_content else {"content": ""},
        )

        return optimized

    def _parse_new_image_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """
        解析新创建的图片元素

        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            element_id: 元素ID

        Returns:
            ElementData: 解析后的图片元素
        """
        # 尝试从内部<img>标签获取src
        img_tag = elem.find('img')
        src = img_tag.get('src', '') if img_tag else elem.get('src', '')

        optimized = ElementData(
            id=element_id,
            type='image',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '100')),
            top=self._parse_px_value(style_dict.get('top', '100')),
            width=self._parse_px_value(style_dict.get('width', '200')),
            height=self._parse_px_value(style_dict.get('height', '150')),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 图片源
            src=src,
            fixedRatio=True,
            # 圆角半径
            radius=self._parse_radius_value(style_dict.get('border-radius', '0')),
        )

        return optimized

    def _parse_image_element(
        self,
        elem: BeautifulSoup,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """
        解析HTML图片元素
        
        Args:
            elem: BeautifulSoup元素
            style_dict: 样式字典
            original: 原始元素
            
        Returns:
            ElementData: 解析后的图片元素
        """
        # 尝试从内部<img>标签获取src
        img_tag = elem.find('img')
        src = original.src
        if img_tag:
            src = img_tag.get('src', original.src)
        else:
            # 如果没有img标签，尝试从外层div获取
            src = elem.get('src', original.src)
        
        optimized = ElementData(
            id=elem.get('data-id'),
            type='image',
            # 位置和尺寸
            left=self._parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=self._parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=self._parse_px_value(style_dict.get('width', ''), default=original.width),
            height=self._parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=self._parse_rotate_value(style_dict.get('transform', '')),
            # 图片源
            src=src,
            fixedRatio=original.fixedRatio,
            # 圆角半径
            radius=self._parse_radius_value(style_dict.get('border-radius', '')),
        )

        # 注意：border-radius样式属性现在已支持，会设置到radius字段
        # 其他不支持的样式属性由LLM优化，但在转换回PPTist元素时会被忽略

        return optimized

