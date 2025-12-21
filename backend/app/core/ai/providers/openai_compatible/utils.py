"""
OpenAI兼容Provider工具函数

提供所有OpenAI兼容Provider共享的工具函数
"""

from typing import Dict, Any
import openai

from app.core.log_utils import get_logger

logger = get_logger(__name__)


def create_openai_client(api_key: str, base_url: str) -> openai.AsyncOpenAI:
    """创建OpenAI异步客户端

    Args:
        api_key: API密钥
        base_url: API基础URL

    Returns:
        OpenAI异步客户端实例
    """
    return openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )


def format_response(response) -> Dict[str, Any]:
    """格式化OpenAI API响应为统一格式

    Args:
        response: OpenAI API响应对象

    Returns:
        格式化后的字典
    """
    return {
        "content": response.choices[0].message.content,
        "model": response.model,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        } if response.usage else {}
    }


def handle_openai_exception(exception, base_url: str = None) -> str:
    """统一处理OpenAI异常

    Args:
        exception: 异常对象
        base_url: API基础URL (可选)

    Returns:
        格式化的错误消息
    """
    error_message = f"API调用失败 ({type(exception).__name__}): {str(exception)}"

    # 简化异常处理逻辑
    if isinstance(exception, openai.APIError):
        status_code = getattr(exception, 'status_code', 'unknown')
        logger.error(f"OpenAI API错误 (状态码: {status_code}): {str(exception)}")
        error_message = f"API调用失败 (状态码: {status_code}): {str(exception)}"

    elif isinstance(exception, openai.APIConnectionError):
        logger.error(f"OpenAI API连接错误: {str(exception)}")
        connection_info = f" ({base_url})" if base_url else ""
        error_message = f"无法连接到API{connection_info}: {str(exception)}"

    elif isinstance(exception, openai.RateLimitError):
        logger.error(f"OpenAI API速率限制: {str(exception)}")
        error_message = f"API速率限制: {str(exception)}"

    elif isinstance(exception, openai.AuthenticationError):
        logger.error(f"OpenAI API认证失败: {str(exception)}")
        error_message = f"API认证失败，请检查API密钥: {str(exception)}"

    return error_message


def get_trace_inputs(model_name: str, base_url: str, messages, temperature: float, max_tokens: int) -> Dict[str, Any]:
    """获取用于MLflow追踪的输入数据

    Args:
        model_name: 模型名称
        base_url: API基础URL
        messages: 消息列表
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        用于MLflow追踪的输入数据字典
    """
    return {
        "model": model_name,
        "base_url": base_url,
        "message_count": len(messages),
        "temperature": temperature,
        "max_tokens": max_tokens
    }