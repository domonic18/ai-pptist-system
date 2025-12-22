"""
图片生成服务
处理图片生成的核心业务逻辑
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.utils.datetime_utils import get_current_iso_string
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability, ImageGenerationResult
from app.repositories.ai_model import AIModelRepository
from app.core.image_config import ImageGenerationConfig

logger = get_logger(__name__)


class ImageGenerationService:
    """图片生成服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_model_repo = AIModelRepository(db)

    async def generate_image(
        self,
        prompt: str,
        ai_model_id: str,
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
            ai_model_id: AI模型ID（用于查找配置）
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
                "ai_model_id": ai_model_id,
                "width": width,
                "height": height,
                "ref_images_count": len(ref_images) if ref_images else 0
            })

            # 从数据库查询模型配置
            if not ai_model_id:
                return self._create_error_result("AI模型ID不能为空")

            ai_model = await self.ai_model_repo.get_model_by_id(ai_model_id)
            if not ai_model:
                return self._create_error_result(f"未找到模型: {ai_model_id}")

            if not ai_model.is_enabled:
                return self._create_error_result(f"模型已禁用: {ai_model.name}")

            # 检查模型是否支持图片生成能力
            if 'image_gen' not in (ai_model.capabilities or []):
                return self._create_error_result(f"模型不支持图片生成能力: {ai_model.name}")

            # 获取provider名称（从provider_mapping获取image_gen的provider）
            provider_mapping = ai_model.provider_mapping or {}
            provider_name = provider_mapping.get('image_gen')

            if not provider_name:
                return self._create_error_result(f"模型未配置图片生成provider: {ai_model.name}")

            # 构建模型配置（与新架构兼容）
            model_config = {
                'id': ai_model.id,
                'model_id': ai_model.id,
                'model_name': ai_model.ai_model_name,
                'name': ai_model.name,
                'ai_model_name': ai_model.ai_model_name,
                'base_url': ai_model.base_url,
                'api_key': ai_model.api_key,
                'capabilities': ai_model.capabilities,
                'provider_mapping': ai_model.provider_mapping,
                'max_tokens': ai_model.max_tokens,
                'context_window': ai_model.context_window,
                'parameters': ai_model.parameters or {}
            }

            logger.info(
                "创建AI图片生成Provider",
                extra={
                    "provider_name": provider_name,
                    "model_id": ai_model.id,
                    "model_name": ai_model.ai_model_name,
                    "base_url": ai_model.base_url,
                    "has_api_key": bool(ai_model.api_key),
                    "api_key_length": len(ai_model.api_key) if ai_model.api_key else 0
                }
            )

            # 使用AIProviderFactory创建provider（新架构）
            image_gen_provider = AIProviderFactory.create_provider(
                capability=ModelCapability.IMAGE_GEN,
                provider_name=provider_name,
                model_config=model_config
            )

            if not image_gen_provider:
                return self._create_error_result(f"不支持的模型provider: {provider_name}")

            # 准备好参数后，调用图片生成
            result = await self._execute_generation(
                image_gen_provider, prompt, width, height, quality, style,
                ref_images, aspect_ratio, resolution
            )

            logger.info("图片生成服务完成", extra={
                "success": result.get("success", False)
            })

            return result

        except Exception as e:
            logger.error("图片生成服务异常", extra={
                "error": str(e)
            })
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
                "success": result.success if hasattr(result, 'success') else False,
                "has_image_url": bool(result.image_url) if hasattr(result, 'image_url') else False
            })

            if result.success:
                return {
                    "success": True,
                    "reused": False,
                    "image": {
                        "url": result.image_url,
                        "model": getattr(provider, 'model', 'Unknown'),
                        "metadata": result.metadata if hasattr(result, 'metadata') else None,
                        "created_at": get_current_iso_string()
                    },
                    "message": "图片生成成功"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message if hasattr(result, 'error_message') else "图片生成失败",
                    "message": "图片生成失败"
                }

        except Exception as e:
            logger.error("提供商图片生成异常", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
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
