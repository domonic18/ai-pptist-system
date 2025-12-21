"""
OpenAI Vision Provider
"""

from typing import List, Dict, Any

from app.core.log_utils import get_logger
from app.core.ai.providers.base.vision import BaseVisionProvider
from app.core.ai.tracker import MLflowTracingMixin
from .client import OpenAIClientMixin

logger = get_logger(__name__)


class OpenAIVisionProvider(BaseVisionProvider, OpenAIClientMixin, MLflowTracingMixin):
    """OpenAI多模态Provider"""
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseVisionProvider.__init__(self, model_config)
        OpenAIClientMixin.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai"
    
    async def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        OpenAI多模态对话接口
        
        Args:
            messages: 对话消息列表（可包含图片）
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            对话结果
        """
        logger.info(
            "OpenAI Vision请求",
            operation="openai_vision",
            model=self.model_config.model_name,
            message_count=len(messages),
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        try:
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
                operation_name="openai_vision",
                inputs={
                    "model": self.model_config.model_name,
                    "message_count": len(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                call_func=call_api
            )
            
        except Exception as e:
            self.handle_error(e)

