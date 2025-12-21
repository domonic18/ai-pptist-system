"""
图片生成服务
处理图片生成的核心业务逻辑
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_model.management_service import ManagementService as AIModelManagementService
from app.core.log_utils import get_logger
from app.utils.datetime_utils import get_current_iso_string
from app.core.image_config import ImageGenerationConfig

logger = get_logger(__name__)


class ImageGenerationService:
    """图片生成服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_model_service = AIModelManagementService(db)

    async def generate_image(
        self,
        prompt: str,
        generation_model: str = "dall-e-3",
        width: int = 1024,
        height: int = 1024,
        quality: str = "standard",
        style: str = "vivid",
        ref_images: list = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K"
    ) -> Dict[str, Any]:
        """
        生成图片

        Args:
            prompt: 图片描述
            generation_model: 生成模型名称
            width: 图片宽度
            height: 图片高度
            quality: 图片质量
            style: 图片风格
            ref_images: 参考图片列表（base64编码）
            aspect_ratio: 图片比例（如 "16:9"）
            resolution: 分辨率（如 "2K"）

        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info("开始图片生成服务", extra={
                "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "generation_model": generation_model,
                "width": width,
                "height": height,
                "ref_images_count": len(ref_images) if ref_images else 0
            })

            # 获取模型配置
            model_config = await self.ai_model_service.get_model_config_for_image_generation(generation_model)
            if not model_config:
                return self._create_error_result("模型不存在")

            # 创建图片生成提供商
            provider = self.ai_model_service.create_image_generation_provider(model_config)
            if not provider:
                return self._create_error_result("不支持的模型类型")

            # 生成图片
            result = await self._execute_generation(
                provider, prompt, width, height, quality, style,
                ref_images, aspect_ratio, resolution
            )

            logger.info("图片生成服务完成", extra={
                "success": result.get("success", False)
            })

            return result

        except Exception as e:
            logger.error("图片生成服务异常", extra={"error": str(e)})
            return self._create_error_result(f"图片生成失败: {str(e)}")

    
    async def _execute_generation(
        self,
        provider,
        prompt: str,
        width: int,
        height: int,
        quality: str,
        style: str,
        ref_images: list = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K"
    ) -> Dict[str, Any]:
        """执行图片生成"""
        try:
            # 使用配置化方式确定图片尺寸
            size = ImageGenerationConfig.get_size_mapping(width, height)

            logger.info("开始调用提供商生成图片", extra={
                "provider_type": type(provider).__name__,
                "size": size,
                "quality": quality,
                "style": style,
                "ref_images_count": len(ref_images) if ref_images else 0
            })

            # 调用提供商生成图片
            result = await provider.generate_image(
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                ref_images=ref_images,
                aspect_ratio=aspect_ratio,
                resolution=resolution
            )

            logger.info("提供商图片生成完成", extra={
                "success": result.success,
                "has_image_url": bool(result.image_url) if hasattr(result, 'image_url') else False
            })

            if result.success:
                return {
                    "success": True,
                    "reused": False,
                    "image": {
                        "url": result.image_url,
                        "model": provider.model_config.name,
                        "metadata": result.metadata,
                        "created_at": get_current_iso_string()
                    },
                    "message": "图片生成成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "图片生成失败"
                }

        except Exception as e:
            logger.error("提供商图片生成异常", extra={"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": "图片生成失败"
            }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "message": "图片生成失败"
        }

    
    