"""
HTML提取器模块
负责从LLM响应中提取和验证HTML内容
"""

import re
from bs4 import BeautifulSoup
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class HTMLExtractor:
    """HTML内容提取器"""

    def extract_from_response(self, llm_response: str) -> str:
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
        html = self._extract_code_blocks(html)

        # 2. 验证HTML是否包含ppt-canvas
        self._validate_ppt_canvas(html)

        # 3. 使用BeautifulSoup验证HTML结构完整性
        result = self._validate_and_extract_canvas(html)

        logger.debug(
            "HTML提取成功",
            operation="extract_html_success",
            result_length=len(result),
            result_preview=result[:200] if result else ""
        )

        return result

    def _extract_code_blocks(self, html: str) -> str:
        """提取代码块中的HTML内容"""
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
        return html

    def _validate_ppt_canvas(self, html: str) -> None:
        """验证HTML是否包含ppt-canvas元素"""
        if '<div class="ppt-canvas"' not in html and '<div class=\'ppt-canvas\'' not in html:
            logger.error(
                "未找到ppt-canvas元素",
                operation="missing_ppt_canvas",
                html_preview=html[:500] if html else ""
            )
            raise ValueError("LLM响应中未找到ppt-canvas元素")

    def _validate_and_extract_canvas(self, html: str) -> str:
        """验证HTML结构并提取canvas内容"""
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
            return str(canvas)

        except Exception as e:
            logger.error(
                "HTML解析失败",
                operation="html_parse_failed",
                error=str(e),
                html_preview=html[:500] if html else ""
            )
            raise ValueError(f"HTML解析失败: {str(e)}")