"""
OpenAI对话Provider
"""

from typing import List, Dict, Union, AsyncGenerator

from app.core.log_utils import get_logger
from app.core.ai.providers.base.chat import BaseChatProvider
from app.core.ai.tracker import MLflowTracingMixin
from .client import OpenAIClientMixin

logger = get_logger(__name__)


class OpenAIChatProvider(BaseChatProvider, OpenAIClientMixin, MLflowTracingMixin):
    """OpenAI对话Provider"""
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseChatProvider.__init__(self, model_config)
        OpenAIClientMixin.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        OpenAI对话接口
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大生成token数
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            对话结果或流式生成器
        """
        logger.info(
            "OpenAI对话请求",
            operation="openai_chat",
            model=self.model_config.model_name,
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
            self.handle_error(e)
    
    async def _sync_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """同步对话"""
        
        async def call_api():
            response = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        
        # 使用MLflow追踪
        return await self._with_mlflow_trace(
            operation_name="openai_chat",
            inputs={
                "model": self.model_config.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
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
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(
                "OpenAI流式对话失败",
                operation="openai_stream_chat_error",
                error=str(e)
            )
            self.handle_error(e)

