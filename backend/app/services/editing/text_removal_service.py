"""
图片文字去除服务
使用文生图大模型去除图片中的文字
"""

import io
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from app.core.log_utils import get_logger
from app.core.storage import download_image_by_key, get_storage_service
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.prompts.utils import load_prompt_template_config
from app.repositories.ai_model import AIModelRepository
from app.services.ai_model.management_service import ManagementService

logger = get_logger(__name__)


class TextRemovalService:
    """
    文字去除服务

    使用文生图大模型的图像编辑能力去除图片中的文字
    """

    def __init__(self, db: AsyncSession):
        """
        初始化文字去除服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.ai_model_repo = AIModelRepository(db)
        self.ai_model_service = ManagementService(db)
        self._providers = []  # 记录创建的 provider，以便关闭

    async def close(self):
        """关闭所有创建的 provider，释放资源"""
        for provider in self._providers:
            try:
                await provider.close()
            except Exception as e:
                logger.warning(f"关闭 AI Provider 失败: {e}")
        self._providers = []

    async def remove_text_from_image(
        self,
        original_cos_key: str,
        ai_model_id: Optional[str] = None,
        text_count: int = 0
    ) -> Dict[str, Any]:
        """
        使用文生图大模型去除图片中的文字

        Args:
            original_cos_key: 原始图片COS Key
            ai_model_id: AI模型ID（可选，如果不提供则使用默认模型）
            text_count: 检测到的文字数量（用于优化提示词）

        Returns:
            Dict: 去除文字后的图片结果
            {
                "original_cos_key": str,
                "edited_cos_key": str,
                "processing_time_ms": int,
                "model_used": str,
                "prompt_used": str,
                "created_at": str
            }
        """
        start_time = datetime.now()

        try:
            logger.info(
                "开始文字去除任务",
                extra={
                    "original_cos_key": original_cos_key,
                    "ai_model_id": ai_model_id,
                    "text_count": text_count
                }
            )

            # 步骤1: 获取图片尺寸和预签名URL
            logger.info("步骤1: 获取图片信息", extra={"cos_key": original_cos_key})
            storage = get_storage_service()

            # 下载图片数据以获取尺寸
            image_data, image_format = await download_image_by_key(original_cos_key, storage)
            temp_image = Image.open(io.BytesIO(image_data))
            width, height = temp_image.size
            temp_image.close()  # 主动关闭以释放资源

            # 生成预签名 URL（用于传递给模型）
            presigned_url = await storage.generate_url(
                original_cos_key,
                expires=3600,
                operation="get"
            )

            logger.info(
                "原始图片信息",
                extra={
                    "width": width,
                    "height": height,
                    "format": image_format,
                    "size_bytes": len(image_data),
                    "presigned_url_length": len(presigned_url)
                }
            )

            # 步骤2: 构建去除文字提示词
            logger.info("步骤2: 构建去除文字提示词")
            prompt = self._build_removal_prompt(text_count)

            # 步骤3: 获取AI模型配置（与 banana_slide_generator 一致）
            logger.info("步骤3: 获取AI模型配置", extra={"ai_model_id": ai_model_id})

            # 如果没有提供 ai_model_id，获取默认的文生图模型
            if not ai_model_id:
                logger.info("未指定AI模型ID，使用默认文生图模型")
                default_model_config = await self.ai_model_service.get_default_model_for_use(
                    capability="image_gen"
                )
                if not default_model_config:
                    raise ValueError("未找到可用的文生图模型，请先配置支持image_gen能力的模型")
                ai_model_id = default_model_config["id"]
                logger.info("使用默认文生图模型", extra={"ai_model_id": ai_model_id})

            ai_model = await self.ai_model_repo.get_model_by_id(ai_model_id)
            if not ai_model:
                raise ValueError(f"未找到AI模型: {ai_model_id}")

            if not ai_model.is_enabled:
                raise ValueError(f"AI模型已禁用: {ai_model.name}")

            if 'image_gen' not in (ai_model.capabilities or []):
                raise ValueError(f"模型不支持图片生成能力: {ai_model.name}")

            provider_mapping = ai_model.provider_mapping or {}
            provider_name = provider_mapping.get('image_gen')
            if not provider_name:
                raise ValueError(f"模型未配置图片生成provider: {ai_model.name}")

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
                "使用模型",
                extra={
                    "ai_model_id": ai_model_id,
                    "model_name": ai_model.ai_model_name,
                    "provider_name": provider_name
                }
            )

            # 步骤4: 创建 Provider 并调用（与 banana_slide_generator 一致）
            logger.info("步骤4: 创建Provider并调用")
            image_gen_provider = AIProviderFactory.create_provider(
                capability=ModelCapability.IMAGE_GEN,
                provider_name=provider_name,
                model_config=model_config
            )

            if not image_gen_provider:
                raise ValueError(f"不支持的模型provider: {provider_name}")

            # 记录 provider 以便后续关闭
            self._providers.append(image_gen_provider)

            # 准备生成参数（与 banana_slide_generator 完全一致）
            generation_params = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "ref_images": [presigned_url],  # 使用预签名 URL
            }

            logger.info(
                "调用AI Provider生成图片",
                extra={
                    "provider_type": type(image_gen_provider).__name__,
                    "model": ai_model.ai_model_name,
                    "width": width,
                    "height": height
                }
            )

            # 直接调用 provider
            result = await image_gen_provider.generate_image(**generation_params)

            if not result or not result.image:
                raise Exception("图片生成失败：返回结果为空")

            logger.info(
                "文生图API调用成功",
                extra={
                    "image_size": result.image.size if result.image else None
                }
            )

            # 步骤5: 将 PIL Image 转换为字节数据（与 banana_slide_generator 一致，直接使用 result.image）
            logger.info("步骤5: 处理生成的图片")
            img_byte_arr = io.BytesIO()
            result.image.save(img_byte_arr, format='PNG')
            edited_image_data = img_byte_arr.getvalue()

            # 步骤6: 上传到COS
            logger.info("步骤6: 上传编辑后的图片到COS")
            edited_cos_key = await self._upload_edited_image(
                edited_image_data,
                original_cos_key
            )

            # 计算处理时间
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            result = {
                "original_cos_key": original_cos_key,
                "edited_cos_key": edited_cos_key,
                "processing_time_ms": processing_time,
                "model_used": ai_model.ai_model_name,
                "prompt_used": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "created_at": datetime.utcnow().isoformat()
            }

            logger.info(
                "文字去除完成",
                extra={
                    "original_cos_key": original_cos_key,
                    "edited_cos_key": edited_cos_key,
                    "processing_time_ms": processing_time,
                    "model_used": ai_model.ai_model_name
                }
            )

            return result

        except Exception as e:
            logger.error(
                "文字去除失败",
                extra={
                    "original_cos_key": original_cos_key,
                    "error": str(e)
                }
            )
            raise

    async def _upload_edited_image(
        self,
        image_data: bytes,
        original_cos_key: str
    ) -> str:
        """
        上传编辑后的图片到COS

        Args:
            image_data: 图片数据
            original_cos_key: 原始图片COS Key

        Returns:
            str: 新图片的COS Key
        """
        storage = get_storage_service()

        # 生成新的COS Key
        # 例如: ai-generated/ppt/xxx/slide_0.png -> image-edited/ppt/xxx/slide_0_no_text.png
        parts = original_cos_key.split('/')
        filename = parts[-1]
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'png'
        new_filename = f"{name_without_ext}_no_text.{ext}"

        # 构建新路径
        if len(parts) > 1:
            path_parts = parts[:-1]
            # 替换第一级目录为image-edited
            path_parts[0] = "image-edited"
            new_cos_key = '/'.join(path_parts) + '/' + new_filename
        else:
            new_cos_key = f"image-edited/{new_filename}"

        # 上传图片
        upload_result = await storage.upload(
            data=image_data,
            key=new_cos_key,
            mime_type=f"image/{ext}"
        )

        logger.info(
            "图片上传成功",
            extra={
                "new_cos_key": new_cos_key,
                "size": upload_result.size
            }
        )

        return new_cos_key

    def _build_removal_prompt(self, text_count: int = 0) -> str:
        """
        构建去除文字的提示词

        Args:
            text_count: 检测到的文字数量（用于优化提示词）

        Returns:
            str: 提示词
        """
        try:
            # 尝试从YAML文件加载提示词模板
            config = load_prompt_template_config("image_editing/text_removal")

            if config.get("template"):
                # 使用Jinja2渲染模板
                from jinja2 import Template
                template = Template(config["template"])
                return template.render(text_count=text_count)

        except Exception as e:
            logger.warning(
                "加载提示词模板失败，使用默认提示词",
                extra={"error": str(e)}
            )

        # 默认提示词（如果模板加载失败）
        base_prompt = """You are an expert image editor. Remove ALL text from this image while preserving the original design, style, layout, and visual elements.

Requirements:
1. Remove ALL text characters, letters, numbers, and symbols from the image
2. Keep the background design, colors, patterns, and visual style exactly the same
3. Maintain the original layout and composition
4. Fill the text areas with appropriate background content that matches the surroundings
5. Do NOT add any new text, numbers, or symbols
6. Preserve shadows, gradients, and visual effects
7. Keep the image quality high and professional

The goal is to create a clean, text-free version of the image that looks like the original design without any text elements."""

        if text_count > 0:
            base_prompt += f"\n\nNote: This image contains approximately {text_count} text elements. Please carefully remove ALL of them while maintaining the design integrity."

        return base_prompt
