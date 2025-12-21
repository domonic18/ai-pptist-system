"""
通义千问 Chat Provider（待实现）
TODO: 实现通义千问对话功能
"""

from typing import List, Dict, Union, AsyncGenerator, Set

from app.core.log_utils import get_logger
from app.core.ai.providers.base.chat import BaseChatProvider
from app.core.ai.models import ModelCapability
from app.core.ai.tracker import MLflowTracingMixin

logger = get_logger(__name__)


class QwenChatProvider(BaseChatProvider, MLflowTracingMixin):
    """通义千问Chat Provider
    
    TODO: 完善通义千问原生API调用
    """
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseChatProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        logger.warning(
            "通义千问 Chat Provider尚未完全实现",
            operation="qwen_chat_init_warning"
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "qwen"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        通义千问对话接口
        
        TODO: 实现通义千问原生API调用
        """
        raise NotImplementedError(
            "通义千问 Chat Provider尚未实现，请使用OpenAI兼容模式或等待后续更新"
        )

