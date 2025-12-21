"""
DALL-E图片生成Provider
"""

from typing import Optional

from app.core.log_utils import get_logger
from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin
from .client import OpenAIClientMixin

logger = get_logger(__name__)


class DALLEProvider(BaseImageGenProvider, OpenAIClientMixin, MLflowTracingMixin):
    """DALL-E图片生成Provider"""
    
    def __init__(self, model_config):
        """初始化Provider"""
        BaseImageGenProvider.__init__(self, model_config)
        OpenAIClientMixin.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai_dalle"
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> ImageGenerationResult:
        """
        DALL-E图片生成接口
        
        Args:
            prompt: 图片描述提示词
            size: 图片尺寸 (1024x1024, 1792x1024, 1024x1792)
            quality: 图片质量 (standard, hd)
            n: 生成图片数量
            **kwargs: 其他参数
            
        Returns:
            ImageGenerationResult: 图片生成结果
        """
        logger.info(
            "DALL-E图片生成请求",
            operation="dalle_generate",
            model=self.model_config.model_name,
            prompt_length=len(prompt),
            size=size,
            quality=quality,
            n=n
        )
        
        try:
            async def call_api():
                response = await self.client.images.generate(
                    model=self.model_config.model_name,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=n
                )
                
                # 获取生成的图片URL
                image_url = response.data[0].url if response.data else None
                
                if not image_url:
                    return ImageGenerationResult(
                        success=False,
                        error_message="API响应中未找到图片数据"
                    )
                
                logger.info(
                    "DALL-E图片生成成功",
                    operation="dalle_generate_success",
                    image_url=image_url
                )
                
                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    metadata={
                        "model": self.model_config.model_name,
                        "size": size,
                        "quality": quality,
                        "revised_prompt": getattr(response.data[0], 'revised_prompt', None)
                    }
                )
            
            # 使用MLflow追踪
            return await self._with_mlflow_trace(
                operation_name="dalle_generate",
                inputs={
                    "model": self.model_config.model_name,
                    "prompt": prompt,
                    "size": size,
                    "quality": quality
                },
                call_func=call_api
            )
            
        except Exception as e:
            logger.error(
                "DALL-E图片生成失败",
                operation="dalle_generate_error",
                error=str(e)
            )
            self.handle_error(e)

