"""
OpenAI兼容Vision Provider（支持多模态）
"""

from typing import List, Dict, Any, Optional
import openai

from app.core.log_utils import get_logger
from app.core.ai.providers.base.vision import BaseVisionProvider
from app.core.ai.tracker import MLflowTracingMixin

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
        self.client = openai.AsyncOpenAI(
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
            # 统一异常处理
            error_message = self._handle_openai_exception(e)
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
        """处理Vision请求"""

        async def call_api():
            response = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return self._format_response(response)

        # 使用MLflow追踪
        return await self._with_mlflow_trace(
            operation_name="openai_compatible_vision",
            inputs=self._get_trace_inputs(messages, temperature, max_tokens),
            call_func=call_api
        )

    def _handle_openai_exception(self, exception) -> str:
        """统一处理OpenAI异常"""
        error_message = f"Vision调用失败 ({type(exception).__name__}): {str(exception)}"

        # 简化异常处理逻辑
        if isinstance(exception, openai.APIError):
            status_code = getattr(exception, 'status_code', 'unknown')
            logger.error(f"OpenAI API错误 (状态码: {status_code}): {str(exception)}")
            error_message = f"API调用失败 (状态码: {status_code}): {str(exception)}"

        elif isinstance(exception, openai.APIConnectionError):
            logger.error(f"OpenAI API连接错误: {str(exception)}")
            error_message = f"无法连接到API ({self.model_config.base_url}): {str(exception)}"

        elif isinstance(exception, openai.RateLimitError):
            logger.error(f"OpenAI API速率限制: {str(exception)}")
            error_message = f"API速率限制: {str(exception)}"

        elif isinstance(exception, openai.AuthenticationError):
            logger.error(f"OpenAI API认证失败: {str(exception)}")
            error_message = f"API认证失败，请检查API密钥: {str(exception)}"

        return error_message

    def _get_trace_inputs(self, messages, temperature, max_tokens) -> Dict[str, Any]:
        """获取用于MLflow追踪的输入数据"""
        return {
            "model": self.model_config.model_name,
            "base_url": self.model_config.base_url,
            "message_count": len(messages),
            "temperature": temperature,
            "max_tokens": max_tokens
        }

    def _format_response(self, response) -> Dict[str, Any]:
        """格式化API响应为统一格式"""
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else {}
        }