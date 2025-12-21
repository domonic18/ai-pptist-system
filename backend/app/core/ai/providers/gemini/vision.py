"""
Gemini Vision Provider
TODO: 需要安装 google-generativeai 库后完善实现
"""

from typing import List, Dict, Any

from app.core.log_utils import get_logger
from app.core.ai.providers.base.vision import BaseVisionProvider
from app.core.ai.tracker import MLflowTracingMixin

logger = get_logger(__name__)


class GeminiVisionProvider(BaseVisionProvider, MLflowTracingMixin):
    """Gemini Vision Provider
    
    TODO: 完善Gemini原生多模态API调用
    """
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseVisionProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        logger.warning(
            "Gemini Vision Provider尚未完全实现",
            operation="gemini_vision_init_warning"
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "gemini"
    
    async def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        Gemini多模态对话接口
        
        TODO: 实现Gemini原生Vision API调用
        """
        raise NotImplementedError(
            "Gemini Vision Provider尚未实现，请使用OpenAI兼容模式或等待后续更新"
        )

