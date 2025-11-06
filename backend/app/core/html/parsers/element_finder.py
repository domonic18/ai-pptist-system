"""
元素查找器模块
负责在HTML中查找PPT元素
"""

from typing import List
from bs4 import BeautifulSoup
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ElementFinder:
    """PPT元素查找器"""

    def find_elements(self, soup: BeautifulSoup) -> List:
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
            # 添加这些div（可能包含装饰性元素），但避免重复
            seen_ids = set()
            for element in ppt_elements:
                if element.get('data-id'):
                    seen_ids.add(element.get('data-id'))

            for div in canvas_divs:
                div_id = div.get('data-id')
                if not div_id or div_id not in seen_ids:
                    ppt_elements.append(div)

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