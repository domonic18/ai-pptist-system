"""
Gemini Imagen Provider
TODO: 需要安装 google-generativeai 库后完善实现
"""

from app.core.log_utils import get_logger
from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin

logger = get_logger(__name__)


class ImagenProvider(BaseImageGenProvider, MLflowTracingMixin):
    """Gemini Imagen Provider
    
    TODO: 完善Gemini Imagen API调用
    """
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        logger.warning(
            "Gemini Imagen Provider尚未完全实现",
            operation="gemini_imagen_init_warning"
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "gemini_imagen"
    
    async def generate_image(
        self,
        prompt: str,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Gemini Imagen图片生成接口
        
        TODO: 实现Gemini Imagen API调用
        """
        raise NotImplementedError(
            "Gemini Imagen Provider尚未实现，请使用其他文生图Provider"
        )

