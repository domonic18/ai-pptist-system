"""
OpenAI共享客户端和工具方法
"""

import openai
from typing import TYPE_CHECKING

from app.core.log_utils import get_logger

if TYPE_CHECKING:
    from app.core.ai.config import ModelConfig

logger = get_logger(__name__)


class OpenAIClientMixin:
    """OpenAI客户端Mixin
    
    提供共享的OpenAI客户端和错误处理
    """
    
    def __init__(self, model_config: 'ModelConfig'):
        """
        初始化OpenAI客户端
        
        Args:
            model_config: 模型配置
        """
        self.client = openai.AsyncOpenAI(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )
        logger.info(
            "OpenAI客户端初始化完成",
            operation="openai_client_init",
            base_url=model_config.base_url,
            model=model_config.model_name
        )
    
    def handle_error(self, e: Exception):
        """
        统一错误处理
        
        Args:
            e: 异常对象
            
        Raises:
            相应的业务异常
        """
        error_msg = str(e)
        
        if isinstance(e, openai.RateLimitError):
            logger.error(
                "OpenAI API调用频率超限",
                operation="openai_rate_limit_error",
                error=error_msg
            )
            raise ValueError(f"API调用频率超限: {error_msg}")
        
        elif isinstance(e, openai.AuthenticationError):
            logger.error(
                "OpenAI API认证失败",
                operation="openai_auth_error",
                error=error_msg
            )
            raise ValueError(f"API认证失败，请检查API密钥: {error_msg}")
        
        elif isinstance(e, openai.APIConnectionError):
            logger.error(
                "OpenAI API连接失败",
                operation="openai_connection_error",
                error=error_msg
            )
            raise ValueError(f"API连接失败: {error_msg}")
        
        elif isinstance(e, openai.BadRequestError):
            logger.error(
                "OpenAI API请求参数错误",
                operation="openai_bad_request_error",
                error=error_msg
            )
            raise ValueError(f"API请求参数错误: {error_msg}")
        
        else:
            logger.error(
                "OpenAI API调用失败",
                operation="openai_generic_error",
                error=error_msg,
                error_type=type(e).__name__
            )
            raise ValueError(f"API调用失败: {error_msg}")

