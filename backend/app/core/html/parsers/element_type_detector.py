"""
元素类型检测器模块
负责根据HTML结构和样式推断元素类型
"""

from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ElementTypeDetector:
    """元素类型检测器"""

    def detect_type(self, element) -> str:
        """
        根据HTML元素推断类型

        Args:
            element: BeautifulSoup元素

        Returns:
            str: 检测到的元素类型
        """
        # 优先级1：检查data-type属性
        element_type = element.get('data-type')
        if element_type:
            return element_type

        # 优先级2：通过class名称推断
        element_class = element.get('class', [])
        if isinstance(element_class, list):
            element_class = ' '.join(element_class)

        if 'shape' in element_class or 'background' in element_class:
            return 'shape'
        if 'text' in element_class or element.get_text(strip=True):
            return 'text'
        if 'image' in element_class:
            return 'image'
        if 'line' in element_class:
            return 'line'

        # 优先级3：通过标签名称推断
        tag_name = element.name.lower()
        if tag_name in ['img', 'image']:
            return 'image'
        if tag_name in ['p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return 'text'

        # 优先级4：通过内容推断
        if element.get_text(strip=True):
            return 'text'
        if element.find('img'):
            return 'image'

        # 默认为shape
        logger.debug(
            "无法确定元素类型，使用默认值",
            operation="default_element_type",
            element_class=element_class,
            tag_name=tag_name
        )
        return 'shape'