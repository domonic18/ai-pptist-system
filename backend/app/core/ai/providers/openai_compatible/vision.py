"""
OpenAI兼容Vision Provider（支持多模态）
"""

from typing import List, Dict, Any, Optional
import openai

from app.core.log_utils import get_logger
from app.core.ai.providers.base.vision import BaseVisionProvider
from app.core.ai.tracker import MLflowTracingMixin
from .utils import (
    create_openai_client,
    format_response,
    handle_openai_exception,
    get_trace_inputs
)

logger = get_logger(__name__)


class OpenAICompatibleVisionProvider(BaseVisionProvider, MLflowTracingMixin):
    """OpenAI兼容Vision Provider

    支持所有兼容OpenAI Vision API的提供商
    """

    def __init__(self, model_config):
        """初始化Provider"""
        BaseVisionProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)

        # 创建OpenAI客户端
        self.client = create_openai_client(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )

        logger.info(
            "OpenAI兼容Vision客户端初始化完成",
            operation="openai_compatible_vision_init",
            base_url=model_config.base_url,
            model=model_config.model_name
        )

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai_compatible"

    async def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> Dict[str, Any]:
        """
        OpenAI兼容多模态对话接口

        Args:
            messages: 对话消息列表（可包含图片）
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            对话结果，包含内容、模型信息和用量统计
        """
        logger.info(
            "OpenAI兼容Vision请求",
            operation="openai_compatible_vision",
            model=self.model_config.model_name,
            base_url=self.model_config.base_url,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:
            return await self._process_vision_request(messages, temperature, max_tokens, **kwargs)
        except Exception as e:
            # 使用工具函数处理OpenAI异常
            error_message = handle_openai_exception(e, self.model_config.base_url)
            logger.error(
                "OpenAI兼容Vision调用失败",
                operation="openai_compatible_vision_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(error_message)

    async def _process_vision_request(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理Vision请求并使用MLflow进行追踪

        Args:
            messages: 对话消息列表（包含图片和文本）
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 传递给OpenAI API的其他参数

        Returns:
            格式化后的响应结果
        """

        async def call_api():
            response = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return format_response(response)

        # 使用MLflow追踪
        return await self._with_mlflow_trace(
            operation_name="openai_compatible_vision",
            inputs=get_trace_inputs(
                self.model_config.model_name,
                self.model_config.base_url,
                messages,
                temperature,
                max_tokens
            ),
            call_func=call_api
        )

