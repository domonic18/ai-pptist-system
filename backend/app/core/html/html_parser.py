"""
HTML解析器模块（重构版）
负责解析LLM返回的HTML，转换回PPTist元素格式
使用模块化组件，提升代码质量和可维护性
"""

from typing import List, Dict
from bs4 import BeautifulSoup

from app.schemas.layout_optimization import ElementData
from app.core.log_utils import get_logger
from app.core.html.id_generator import PPTIDGenerator
from .parsers import HTMLExtractor, ElementFinder, ElementTypeDetector
from .html_utils import parse_inline_style, parse_px_value, parse_rotate_value, parse_radius_value

logger = get_logger(__name__)


class HTMLParser:
    """HTML到PPTist元素的解析器（重构版）"""

    def __init__(self):
        self.html_extractor = HTMLExtractor()
        self.element_finder = ElementFinder()
        self.type_detector = ElementTypeDetector()
        self.id_generator = PPTIDGenerator()

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
        return self.html_extractor.extract_from_response(llm_response)

    def parse_html_to_elements(
        self,
        html_content: str,
        original_elements: List[ElementData]
    ) -> List[ElementData]:
        """
        解析HTML内容为PPTist元素列表

        Args:
            html_content: HTML内容
            original_elements: 原始元素列表

        Returns:
            List[ElementData]: 解析后的元素列表
        """
        if not html_content:
            raise ValueError("HTML内容为空")

        if not original_elements:
            raise ValueError("原始元素列表为空")

        logger.info(
            "HTML解析开始",
            operation="parse_html_start",
            html_length=len(html_content),
            original_elements_count=len(original_elements)
        )

        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 构建原始元素ID映射
            original_map = {el.id: el for el in original_elements}

            # 查找所有PPT元素
            ppt_elements = self.element_finder.find_elements(soup)

            logger.info(
                "找到HTML元素",
                operation="find_html_elements",
                found_elements_count=len(ppt_elements)
            )

            optimized_elements = []

            for elem in ppt_elements:
                element_id = elem.get('data-id')
                element_type = elem.get('data-type')

                # 如果没有明确的类型，自动检测
                if not element_type:
                    element_type = self.type_detector.detect_type(elem)

                # 如果没有ID，生成符合nanoid(10)规范的新ID
                if not element_id:
                    element_id = self.id_generator.generate_id()
                    logger.info(
                        "为无ID元素自动生成新ID",
                        operation="generate_new_id",
                        element_id=element_id,
                        element_type=element_type
                    )

                # 查找原始元素
                original = original_map.get(element_id)
                if not original:
                    logger.warning(
                        "未找到原始元素，但保留为新生成的装饰元素",
                        operation="treat_as_new_element",
                        element_id=element_id
                    )

                # 解析样式
                style_dict = parse_inline_style(elem.get('style', ''))

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
                    elif element_type == 'svg':
                        if original:
                            optimized = self._parse_svg_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_svg_element(elem, style_dict, element_id)
                    elif element_type == 'image':
                        if original:
                            optimized = self._parse_image_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_image_element(elem, style_dict, element_id)
                    elif element_type == 'line':
                        if original:
                            optimized = self._parse_line_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_line_element(elem, style_dict, element_id)
                    else:
                        # 默认为shape
                        if original:
                            optimized = self._parse_shape_element(elem, style_dict, original)
                        else:
                            optimized = self._parse_new_shape_element(elem, style_dict, element_id)

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

            # 验证结果
            if len(optimized_elements) == 0:
                logger.warning(
                    "未找到任何可优化的元素",
                    operation="no_optimized_elements",
                    html_content_length=len(html_content),
                    original_elements_count=len(original_elements)
                )
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
                error_type=type(e).__name__
            )
            return original_elements

    def _parse_text_element(
        self,
        elem,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """解析文本元素（保持原有逻辑）"""
        # 提取文本内容
        text_content = elem.get_text(strip=True)

        # 构建更新的元素
        optimized = ElementData(
            id=elem.get('data-id'),
            type='text',
            # 位置和尺寸（只有解析到的才设置）
            left=parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=parse_px_value(style_dict.get('width', ''), default=original.width),
            height=parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 文本内容
            content=text_content,
            # 字体样式
            defaultFontName=style_dict.get('font-family', '').strip('"\'') or original.defaultFontName,
            defaultColor=style_dict.get('color', '') or original.defaultColor,
            lineHeight=float(style_dict.get('line-height', original.lineHeight or 1.0)),
            fontSize=parse_px_value(style_dict.get('font-size', ''), default=original.fontSize),
            fontWeight=style_dict.get('font-weight', '') or original.fontWeight,
            textAlign=style_dict.get('text-align', '') or original.textAlign,
            wordSpace=parse_px_value(style_dict.get('word-spacing', ''), default=original.wordSpace),
            paragraphSpace=parse_px_value(style_dict.get('margin-bottom', ''), default=original.paragraphSpace),
        )

        return optimized

    def _parse_new_text_element(
        self,
        elem,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """解析新创建的文本元素"""
        # 提取文本内容
        text_content = elem.get_text(strip=True)

        # 构建新元素
        optimized = ElementData(
            id=element_id,
            type='text',
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '100')),
            top=parse_px_value(style_dict.get('top', '100')),
            width=parse_px_value(style_dict.get('width', '200')),
            height=parse_px_value(style_dict.get('height', '50')),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 文本内容
            content=text_content or '新文本',
            # 默认字体样式
            defaultFontName=style_dict.get('font-family', '').strip('"\'') or 'Arial',
            defaultColor=style_dict.get('color', '#333333'),
            lineHeight=1.5,
            fontSize=parse_px_value(style_dict.get('font-size', '16')),
            fontWeight=style_dict.get('font-weight', 'normal'),
            textAlign=style_dict.get('text-align', 'left'),
        )

        return optimized

    def _parse_shape_element(
        self,
        elem,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """解析形状元素（保持原有逻辑）"""
        # 提取形状内部文字
        shape_text_elem = elem.find(class_='shape-text')
        text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''

        # 处理背景颜色或渐变
        fill_value = original.fill
        if 'background-color' in style_dict:
            fill_value = style_dict['background-color']
        elif 'background' in style_dict:
            bg = style_dict['background']
            if 'gradient' not in bg.lower():
                fill_value = bg

        optimized = ElementData(
            id=elem.get('data-id'),
            type='shape',
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=parse_px_value(style_dict.get('width', ''), default=original.width),
            height=parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 形状样式
            fill=fill_value,
            outline=original.outline,  # 保持原始轮廓
            text={"content": text_content} if text_content else {"content": ""},
            # 保留原始元素的viewBox、path等关键字段（前端shape元素必需）
            viewBox=original.viewBox,
            path=original.path,
            fixedRatio=original.fixedRatio,
        )

        return optimized

    def _parse_new_shape_element(
        self,
        elem,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """解析新创建的形状元素"""
        # 提取形状内部文字
        shape_text_elem = elem.find(class_='shape-text')
        text_content = shape_text_elem.get_text(strip=True) if shape_text_elem else ''

        # 处理背景颜色或渐变
        fill_value = style_dict.get('background-color', '#ffffff')
        if 'background' in style_dict:
            bg = style_dict['background']
            if 'gradient' in bg.lower():
                # 提取gradient中的第一个颜色
                import re
                color_match = re.search(r'#[0-9a-fA-F]{6}', bg)
                if color_match:
                    fill_value = color_match.group(0)
                else:
                    fill_value = '#47acc5'
            else:
                fill_value = bg

        # 解析尺寸
        width = parse_px_value(style_dict.get('width', '100'))
        height = parse_px_value(style_dict.get('height', '100'))

        # 为新shape元素创建默认的viewBox和path（矩形）
        # viewBox使用元素的宽高，path创建一个矩形路径
        default_viewBox = [width, height]
        default_path = f'M 0 0 L {width} 0 L {width} {height} L 0 {height} Z'

        optimized = ElementData(
            id=element_id,
            type='shape',
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '100')),
            top=parse_px_value(style_dict.get('top', '100')),
            width=width,
            height=height,
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 形状样式
            fill=fill_value,
            outline=None,
            text={"content": text_content} if text_content else {"content": ""},
            # 设置默认的viewBox和path，确保前端能正确渲染
            viewBox=default_viewBox,
            path=default_path,
            fixedRatio=False,
        )

        return optimized

    def _parse_image_element(
        self,
        elem,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """解析图片元素（保持原有逻辑）"""
        # 尝试从内部<img>标签获取src
        img_tag = elem.find('img')
        src = img_tag.get('src', '') if img_tag else elem.get('src', '')

        optimized = ElementData(
            id=elem.get('data-id'),
            type='image',
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=parse_px_value(style_dict.get('width', ''), default=original.width),
            height=parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 图片源
            src=src or original.src,
            fixedRatio=original.fixedRatio,
            # 圆角半径
            radius=parse_radius_value(style_dict.get('border-radius', '')),
        )

        return optimized

    def _parse_new_image_element(
        self,
        elem,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """解析新创建的图片元素"""
        # 尝试从内部<img>标签获取src
        img_tag = elem.find('img')
        src = img_tag.get('src', '') if img_tag else elem.get('src', '')

        optimized = ElementData(
            id=element_id,
            type='image',
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '100')),
            top=parse_px_value(style_dict.get('top', '100')),
            width=parse_px_value(style_dict.get('width', '200')),
            height=parse_px_value(style_dict.get('height', '150')),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # 图片源
            src=src,
            fixedRatio=True,
            # 圆角半径
            radius=parse_radius_value(style_dict.get('border-radius', '0')),
        )

        return optimized

    def _parse_line_element(
        self,
        elem,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """解析线条元素（保持原有逻辑）"""
        # 线条使用形状类型，但处理特殊样式
        optimized = self._parse_shape_element(elem, style_dict, original)
        optimized.type = 'line'
        return optimized

    def _parse_new_line_element(
        self,
        elem,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """解析新创建的线条元素"""
        # 线条使用形状类型，但处理特殊样式
        optimized = self._parse_new_shape_element(elem, style_dict, element_id)
        optimized.type = 'line'
        return optimized

    def _parse_svg_element(
        self,
        elem,
        style_dict: Dict[str, str],
        original: ElementData
    ) -> ElementData:
        """解析SVG元素（保持原有逻辑）
        提取SVG内部的path信息并转换为shape类型
        """
        # 提取viewBox属性 - 检查大小写
        viewBox_attr = elem.get('viewBox', '') or elem.get('viewbox', '') or elem.get('viewBox'.lower(), '')
        viewBox = None




        if viewBox_attr:
            try:
                viewBox_parts = [float(x.strip()) for x in viewBox_attr.split()]
                if len(viewBox_parts) == 4:
                    # viewBox格式: [minX, minY, width, height]
                    viewBox = [viewBox_parts[2], viewBox_parts[3]]
            except (ValueError, AttributeError) as e:
                pass

        # 提取所有path元素的d属性
        path_elems = elem.find_all('path')
        path_d_list = []
        for path_elem in path_elems:
            d_attr = path_elem.get('d', '')
            if d_attr:
                path_d_list.append(d_attr)

        # 使用提取的路径或原始路径
        path_d = ''
        if path_d_list:
            if len(path_d_list) == 1:
                path_d = path_d_list[0]
            else:
                # 多个路径时，使用第一个
                path_d = path_d_list[0]
                logger.debug(
                    "发现多个SVG路径，仅使用第一个",
                    operation="svg_multiple_paths",
                    element_id=elem.get('data-id'),
                    path_count=len(path_d_list)
                )
        else:
            path_d = original.path

        # 如果没有路径，使用默认矩形
        if not path_d:
            elem_width = parse_px_value(style_dict.get('width', ''), default=original.width or 40)
            elem_height = parse_px_value(style_dict.get('height', ''), default=original.height or 40)
            path_d = f'M 0 0 L {elem_width} 0 L {elem_width} {elem_height} L 0 {elem_height} Z'

        # 确定最终使用的viewBox
        if viewBox:
            # 如果从SVG中提取到了viewBox，优先使用它
            final_viewBox = viewBox
        else:
            # 如果没有从SVG提取到viewBox，使用元素尺寸
            elem_width = parse_px_value(style_dict.get('width', ''), default=original.width or 40)
            elem_height = parse_px_value(style_dict.get('height', ''), default=original.height or 40)
            final_viewBox = [elem_width, elem_height]


        optimized = ElementData(
            id=elem.get('data-id'),
            type='shape',  # 使用shape类型
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '0'), default=original.left),
            top=parse_px_value(style_dict.get('top', '0'), default=original.top),
            width=parse_px_value(style_dict.get('width', ''), default=original.width),
            height=parse_px_value(style_dict.get('height', ''), default=original.height),
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # SVG路径信息
            viewBox=final_viewBox,
            path=path_d or original.path,
            fixedRatio=original.fixedRatio,
            # 样式
            fill=original.fill,
            # 保持原始文本
            text=original.text,
        )

        return optimized

    def _parse_new_svg_element(
        self,
        elem,
        style_dict: Dict[str, str],
        element_id: str
    ) -> ElementData:
        """解析新创建的SVG元素
        提取SVG内部的path信息并转换为shape类型，以便前端复用shape渲染逻辑
        """
        # 提取viewBox属性 - 检查大小写
        viewBox_attr = elem.get('viewBox', '') or elem.get('viewbox', '') or elem.get('viewBox'.lower(), '')
        viewBox = None
        if viewBox_attr:
            try:
                viewBox_parts = [float(x.strip()) for x in viewBox_attr.split()]
                if len(viewBox_parts) == 4:
                    # viewBox格式: [minX, minY, width, height]
                    viewBox = [viewBox_parts[2], viewBox_parts[3]]
            except (ValueError, AttributeError):
                pass

        # 提取所有path元素的d属性，并合并为一个复杂的路径
        path_elems = elem.find_all('path')
        path_d_list = []
        for path_elem in path_elems:
            d_attr = path_elem.get('d', '')
            if d_attr:
                path_d_list.append(d_attr)

        # 合并所有路径，如果只有一个路径则直接使用，否则需要特殊处理
        # 注意：多个path可能需要用<g>标签分组，这里简化处理
        path_d = ''
        if path_d_list:
            # 如果有多个path，尝试合并（简化处理）
            if len(path_d_list) == 1:
                path_d = path_d_list[0]
            else:
                # 多个路径时，组合成一个组（实际渲染时前端需要支持多path）
                # 这里先使用第一个路径，后续可以优化
                path_d = path_d_list[0]
                logger.debug(
                    "发现多个SVG路径，仅使用第一个",
                    operation="svg_multiple_paths",
                    element_id=element_id,
                    path_count=len(path_d_list)
                )

        # 解析尺寸
        width = parse_px_value(style_dict.get('width', '40'))
        height = parse_px_value(style_dict.get('height', '40'))

        # 如果没有路径，使用默认矩形
        if not path_d:
            path_d = f'M 0 0 L {width} 0 L {width} {height} L 0 {height} Z'

        # 使用shape类型，让前端能复用现有的shape渲染逻辑
        optimized = ElementData(
            id=element_id,
            type='shape',  # 使用shape类型而不是svg类型
            # 位置和尺寸
            left=parse_px_value(style_dict.get('left', '100')),
            top=parse_px_value(style_dict.get('top', '100')),
            width=width,
            height=height,
            rotate=parse_rotate_value(style_dict.get('transform', '')),
            # SVG路径信息保存在path和viewBox中
            viewBox=viewBox or [width, height],
            path=path_d or f'M 0 0 L {width} 0 L {width} {height} L 0 {height} Z',
            fixedRatio=False,
            # 样式
            fill='#ffffff',
            # 空文本
            text={"content": ""},
        )

        return optimized