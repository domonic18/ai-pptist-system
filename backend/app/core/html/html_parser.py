"""
HTML解析器模块
负责解析LLM返回的HTML，转换回PPTist元素格式
"""

from typing import List, Dict
import re
from bs4 import BeautifulSoup

from app.schemas.layout_optimization import ElementData
from app.core.log_utils import get_logger

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
        html = llm_response.strip()
        
        # 1. 如果包含markdown代码块，提取代码块内容
        if '```html' in html:
            match = re.search(r'```html\s*(.*?)\s*```', html, re.DOTALL)
            if match:
                html = match.group(1).strip()
        elif '```' in html:
            match = re.search(r'```\s*(.*?)\s*```', html, re.DOTALL)
            if match:
                html = match.group(1).strip()
        
        # 2. 验证HTML是否包含ppt-canvas
        if '<div class="ppt-canvas"' not in html and '<div class=\'ppt-canvas\'' not in html:
            raise ValueError("LLM响应中未找到ppt-canvas元素")
        
        # 3. 使用BeautifulSoup验证HTML结构完整性
        soup = BeautifulSoup(html, 'html.parser')
        canvas = soup.find('div', class_='ppt-canvas')
        
        if not canvas:
            raise ValueError("无法解析ppt-canvas元素")
        
        # 返回完整的canvas HTML（包括所有子元素）
        return str(canvas)
    
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
        
        for elem in ppt_elements:
            element_id = elem.get('data-id')
            element_type = elem.get('data-type')
            
            logger.debug(
                "解析HTML元素",
                operation="parse_html_element",
                element_id=element_id,
                element_type=element_type
            )
            
            if not element_id or not element_type:
                logger.warning(
                    "跳过无效元素",
                    operation="skip_invalid_element",
                    element_html=str(elem)[:200]
                )
                continue
            
            # 获取原始元素
            original = original_map.get(element_id)
            if not original:
                logger.warning(
                    "未找到原始元素",
                    operation="skip_missing_original",
                    element_id=element_id
                )
                continue
            
            # 解析样式
            style_dict = self._parse_inline_style(elem.get('style', ''))
            
            # 根据类型解析元素
            try:
                if element_type == 'text':
                    optimized = self._parse_text_element(elem, style_dict, original)
                elif element_type == 'shape':
                    optimized = self._parse_shape_element(elem, style_dict, original)
                elif element_type == 'image':
                    optimized = self._parse_image_element(elem, style_dict, original)
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
                # 解析失败时使用原始元素
                optimized_elements.append(original)
        
        logger.info(
            "HTML解析完成",
            operation="parse_html_complete",
            optimized_elements_count=len(optimized_elements),
            found_element_ids=[el.id for el in optimized_elements]
        )
        
        return optimized_elements
    
    def _find_ppt_elements(self, soup: BeautifulSoup) -> List:
        """
        查找所有PPT元素，使用多种选择器策略
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            List: 找到的元素列表
        """
        # 方法1：通过class查找
        ppt_elements = soup.find_all(class_='ppt-element')
        
        if ppt_elements:
            logger.debug(
                "使用主选择器查找元素",
                operation="primary_element_search",
                found_count=len(ppt_elements)
            )
            return ppt_elements
        
        # 方法2：通过包含data-id属性的div查找
        ppt_elements = soup.find_all('div', attrs={'data-id': True})
        
        if ppt_elements:
            logger.info(
                "使用备用选择器查找元素",
                operation="fallback_element_search",
                found_count=len(ppt_elements)
            )
            return ppt_elements
        
        # 方法3：查找所有div，然后筛选有data-id的
        all_divs = soup.find_all('div')
        ppt_elements = [div for div in all_divs if div.get('data-id')]
        
        logger.info(
            "使用通用选择器查找元素",
            operation="generic_element_search",
            found_count=len(ppt_elements)
        )
        
        return ppt_elements
    
    def _parse_inline_style(self, style_str: str) -> Dict[str, str]:
        """
        解析内联样式字符串为字典
        
        Args:
            style_str: 样式字符串，如 "position: absolute; left: 100px"
            
        Returns:
            Dict[str, str]: 样式字典
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
    
    def _parse_px_value(self, value: str, default: float = 0.0) -> float:
        """
        解析px值，支持auto等特殊值
        
        Args:
            value: 如 "100px" 或 "100" 或 "auto"
            default: 当无法解析时返回的默认值
            
        Returns:
            float: 数值
        """
        if not value:
            return default
        
        value = str(value).strip().lower()
        
        # 如果是auto或其他非数值，返回默认值
        if value == 'auto' or value == 'inherit' or value == 'initial':
            return default
        
        # 移除px后缀
        if value.endswith('px'):
            value = value[:-2]
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _parse_rotate_value(self, transform: str) -> float:
        """
        从transform中解析旋转角度
        
        Args:
            transform: 如 "rotate(15deg)"
            
        Returns:
            float: 角度值
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
        )
        
        # 注意：border-radius等样式属性在PPTist元素中可能不支持
        # 这些样式由LLM优化，但在转换回PPTist元素时会被忽略
        
        return optimized

