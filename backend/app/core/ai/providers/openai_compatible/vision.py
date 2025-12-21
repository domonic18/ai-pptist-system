"""
OpenAI兼容Vision Provider（支持多模态）
"""

from typing import List, Dict, Any
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
    ) -> str:
        """
        OpenAI兼容多模态对话接口
        
        Args:
            messages: 对话消息列表（可包含图片）
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            对话结果
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
                operation_name="openai_compatible_vision",
                inputs={
                    "model": self.model_config.model_name,
                    "base_url": self.model_config.base_url,
                    "message_count": len(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                call_func=call_api
            )
            
        except Exception as e:
            logger.error(
                "OpenAI兼容Vision调用失败",
                operation="openai_compatible_vision_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Vision调用失败: {str(e)}")

