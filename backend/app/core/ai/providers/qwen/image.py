"""
通义万相 Image Provider（待实现）
TODO: 实现通义万相图片生成功能
"""

from typing import Dict, Any

from app.core.log_utils import get_logger
from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ModelCapability
from app.core.ai.tracker import MLflowTracingMixin

logger = get_logger(__name__)


class QwenImageProvider(BaseImageGenProvider, MLflowTracingMixin):
    """通义万相 Image Provider
    
    TODO: 完善通义万相原生API调用
    """
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        logger.warning(
            "通义万相 Provider尚未完全实现",
            operation="qwen_image_init_warning"
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "qwen"
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        """
        通义万相图片生成接口
        
        TODO: 实现通义万相原生API调用
        """
        raise NotImplementedError(
            "通义万相 Provider尚未实现，请等待后续更新"
        )

