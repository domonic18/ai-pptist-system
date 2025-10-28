"""
搜索工具函数
包含搜索相关的通用工具函数
"""

from typing import List, Dict, Any
from app.core.log_utils import get_logger

logger = get_logger(__name__)


def format_search_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    格式化搜索结果

    Args:
        results: 原始搜索结果列表

    Returns:
        格式化后的搜索结果
    """
    formatted = []
    for result in results:
        try:
            formatted_result = {
                "id": result.get("id", ""),
                "prompt": result.get("prompt", ""),
                "model_name": result.get("model_name", ""),
                "width": result.get("width"),
                "height": result.get("height"),
                "file_size": result.get("file_size"),
                "mime_type": result.get("mime_type", ""),
                "created_at": result.get("created_at"),
                "cos_key": result.get("cos_key"),
                "cos_bucket": result.get("cos_bucket"),
                "cos_region": result.get("cos_region"),
                "access_url": result.get("access_url"),
                "match_type": result.get("match_type", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "score": result.get("score", 0),
                "search_context": result.get("search_context", ""),
                "metadata": result.get("metadata", {})
            }
            formatted.append(formatted_result)
        except Exception as e:
            logger.warning(f"格式化搜索结果失败: {e}")
            continue

    return formatted


def validate_search_query(query: str) -> bool:
    """
    验证搜索查询

    Args:
        query: 搜索查询

    Returns:
        是否有效
    """
    if not query or not query.strip():
        return False

    # 检查查询长度
    if len(query.strip()) < 2:
        return False

    # 检查是否包含有效字符
    import re
    if not re.search(r'[a-zA-Z0-9\u4e00-\u9fff]', query):
        return False

    return True