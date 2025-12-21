"""
OpenAI兼容对话Provider（支持DeepSeek、智谱AI等）
"""

from typing import List, Dict, Union, AsyncGenerator, Any, Optional

from app.core.log_utils import get_logger
from app.core.ai.providers.base.chat import BaseChatProvider
from app.core.ai.tracker import MLflowTracingMixin
from .utils import (
    create_openai_client,
    format_response,
    handle_openai_exception,
    get_trace_inputs
)

logger = get_logger(__name__)


class OpenAICompatibleChatProvider(BaseChatProvider, MLflowTracingMixin):
    """OpenAI兼容对话Provider

    支持所有兼容OpenAI API的提供商，包括：
    - DeepSeek
    - 智谱AI (GLM)
    - 月之暗面 (Moonshot)
    - 百川智能
    - 等等
    """

    def __init__(self, model_config):
        """初始化Provider"""
        BaseChatProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)

        # 创建OpenAI客户端
        self.client = create_openai_client(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )

        logger.info(
            "OpenAI兼容客户端初始化完成",
            operation="openai_compatible_init",
            base_url=model_config.base_url,
            model=model_config.model_name
        )

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai_compatible"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, AsyncGenerator[str, None]]:
        """
        OpenAI兼容对话接口

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            - 当 stream=False 时，返回字典：{"content": str, "model": str, "usage": dict}
            - 当 stream=True 时，返回流式生成器（逐块返回文本）
        """
        logger.info(
            "OpenAI兼容对话请求",
            operation="openai_compatible_chat",
            model=self.model_config.model_name,
            base_url=self.model_config.base_url,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

        try:
            if stream:
                return self._stream_chat(messages, temperature, max_tokens, **kwargs)
            else:
                return await self._sync_chat(messages, temperature, max_tokens, **kwargs)
        except Exception as e:
            # 使用工具函数处理OpenAI异常
            error_message = handle_openai_exception(e, self.model_config.base_url)
            logger.error(
                "对话请求失败",
                operation="openai_compatible_chat_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(error_message) from e

    async def _sync_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict:
        """
        同步对话（返回字典格式）

        使用MLflow追踪并处理API调用
        """
        async def call_api():
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_config.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return format_response(response)
            except Exception as e:
                # 使用统一异常处理函数
                error_message = handle_openai_exception(e, self.model_config.base_url)
                logger.error(
                    "同步对话失败",
                    operation="sync_chat_error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise ValueError(error_message) from e

        # 使用MLflow追踪
        return await self._with_mlflow_trace(
            operation_name="openai_compatible_chat",
            inputs=get_trace_inputs(
                self.model_config.model_name,
                self.model_config.base_url,
                messages,
                temperature,
                max_tokens
            ),
            call_func=call_api
        )

    async def _stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        logger.info(
            "开始OpenAI兼容流式对话",
            operation="stream_chat_start",
            model=self.model_config.model_name,
            base_url=self.model_config.base_url,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:
            # 调用 API
            stream = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            # 处理流式响应
            async for content in self._process_stream(stream):
                yield content

        except Exception as e:
            # 使用工具函数处理OpenAI异常
            error_message = handle_openai_exception(e, self.model_config.base_url)
            logger.error(
                "流式对话失败",
                operation="stream_chat_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(error_message) from e

    async def _process_stream(self, stream) -> AsyncGenerator[str, None]:
        """处理流式响应"""
        chunk_count = 0
        has_content = False

        try:
            async for chunk in stream:
                chunk_count += 1
                content = self._extract_chunk_content(chunk)

                if content:
                    has_content = True
                    logger.debug(f"接收chunk #{chunk_count}: {len(content)} 字符")
                    yield content

            # 记录流处理结果
            if not has_content:
                logger.warning("流式对话完成但没有收到任何内容")
            else:
                logger.info(f"流式对话完成，共处理 {chunk_count} 个chunks")

        except UnboundLocalError as exc:
            # 只有在没有收到内容时才需要特殊处理MLflow bug
            if has_content:
                logger.warning("MLflow autolog bug但已收到内容，忽略")
                return

            logger.error("检测到MLflow bug与空响应", error=str(exc))
            raise ValueError("API返回空响应或无效响应。请检查API配置、模型名称和服务状态。") from exc

    def _extract_chunk_content(self, chunk) -> Optional[str]:
        """
        从流式响应chunk中提取内容

        Args:
            chunk: OpenAI流式响应的单个chunk

        Returns:
            提取到的内容字符串，如果无内容则返回None
        """
        # 快速检查是否有错误信息
        if hasattr(chunk, 'error'):
            logger.error(f"Chunk包含错误: {chunk.error}")
            return None

        # 验证chunk结构
        if not chunk.choices or not chunk.choices[0]:
            return None

        choice = chunk.choices[0]

        # 记录结束原因（如果有）
        if getattr(choice, 'finish_reason', None):
            logger.info(f"流结束原因: {choice.finish_reason}")

        # 提取delta内容（如果存在）
        delta = getattr(choice, 'delta', None)
        if delta and getattr(delta, 'content', None):
            return delta.content

        return None