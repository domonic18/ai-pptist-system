"""
JSON工具模块
提供统一的JSON处理函数
"""

import json
from typing import Dict, Any


class ResponseParser:
    """响应解析器"""

    @staticmethod
    def parse_json_response(ai_response: str) -> Dict[str, Any]:
        """
        解析JSON格式的AI响应

        Args:
            ai_response: AI响应内容

        Returns:
            Dict[str, Any]: 解析后的JSON数据

        Raises:
            ValueError: 解析失败时抛出
        """
        try:
            cleaned_response = ai_response.strip()

            # 清理可能的非JSON前缀/后缀
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]

            return json.loads(cleaned_response)

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI response as JSON: {str(e)}") from e

    @staticmethod
    def validate_slides_structure(data: Dict[str, Any]) -> None:
        """验证幻灯片数据结构"""
        if not isinstance(data, dict) or 'slides' not in data:
            raise ValueError("Invalid response format: missing 'slides' field")

        if not isinstance(data['slides'], list):
            raise ValueError("Invalid response format: 'slides' must be a list")