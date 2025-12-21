"""
文生图能力Provider基类
"""

from abc import abstractmethod
from typing import Set

from app.core.ai.base import BaseAIProvider
from app.core.ai.models import ModelCapability, ImageGenerationResult


class BaseImageGenProvider(BaseAIProvider):
    """文生图Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        """获取支持的能力"""
        return {ModelCapability.IMAGE_GEN}
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片接口
        
        Args:
            prompt: 图片描述提示词
            **kwargs: 其他参数（如size, quality, ref_images等）
            
        Returns:
            ImageGenerationResult: 图片生成结果
        """
        pass

