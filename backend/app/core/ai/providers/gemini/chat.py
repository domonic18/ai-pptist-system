"""
Gemini Chat Provider
TODO: 需要安装 google-generativeai 库后完善实现
"""

from typing import List, Dict, Union, AsyncGenerator

from app.core.log_utils import get_logger
from app.core.ai.providers.base.chat import BaseChatProvider
from app.core.ai.tracker import MLflowTracingMixin

logger = get_logger(__name__)


class GeminiChatProvider(BaseChatProvider, MLflowTracingMixin):
    """Gemini对话Provider
    
    TODO: 完善Gemini原生API调用
    需要安装: pip install google-generativeai
    """
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseChatProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        logger.warning(
            "Gemini Chat Provider尚未完全实现",
            operation="gemini_chat_init_warning"
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "gemini"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Gemini对话接口
        
        TODO: 实现Gemini原生API调用
        """
        raise NotImplementedError(
            "Gemini Chat Provider尚未实现，请使用OpenAI兼容模式或等待后续更新"
        )

