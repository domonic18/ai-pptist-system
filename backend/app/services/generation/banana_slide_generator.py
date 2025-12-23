"""
Banana幻灯片生成器
负责调用AI Provider生成单张幻灯片的图片
"""

import time
from typing import Dict, Any
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.services.generation.banana_task_manager import BananaTaskManager
from app.services.generation.banana_prompt_service import BananaPromptService
from app.repositories.ai_model import AIModelRepository
from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class BananaSlideGenerator:
    """Banana幻灯片图片生成器"""

    def __init__(self, db: AsyncSession = None):
        """
        初始化生成器
        
        Args:
            db: 数据库会话（可选，用于查询模型配置）
        """
        self.db = db
        self.prompt_service = BananaPromptService()

    @staticmethod
    def build_cos_path(task_id: str, slide_index: int) -> str:
        """
        构建 COS 路径（强制使用 ai-generated/ppt/ 前缀）

        Args:
            task_id: 生成任务ID
            slide_index: 幻灯片索引

        Returns:
            str: COS 路径
        """
        # ⚠️ 强制使用 ai-generated/ppt/ 前缀，避免metainsight搜索
        return f"ai-generated/ppt/{task_id}/slide_{slide_index}.png"

    async def generate_single_slide(
        self,
        slide_index: int,
        slide_data: Dict[str, Any],
        template_image_url: str,
        generation_model: str,
        canvas_size: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        生成单张幻灯片图片

        Args:
            slide_index: 幻灯片索引
            slide_data: 幻灯片数据（包含title和points）
            template_image_url: 模板图片URL
            generation_model: AI模型ID（用于从数据库获取配置）
            canvas_size: 画布尺寸 {width, height}

        Returns:
            Dict: 生成结果，包含pil_image、generation_time等
        """
        start_time = time.time()
        logger.info("开始生成幻灯片图片", extra={
            "slide_index": slide_index,
            "slide_title": slide_data.get("title"),
            "generation_model": generation_model
        })

        try:
            # 1. 生成提示词
            prompt = self.prompt_service.generate_slide_prompt(
                title=slide_data["title"],
                points=slide_data["points"],
                ppt_title=slide_data.get("ppt_title", "PPT演示"),
                page_index=slide_index + 1,
                total_pages=slide_data.get("total_pages", 1)
            )

            logger.debug("生成提示词", extra={
                "slide_index": slide_index,
                "prompt_length": len(prompt)
            })

            # 2. 从数据库获取模型配置
            if not self.db:
                raise ValueError("数据库会话未初始化，无法获取模型配置")
            
            ai_model_repo = AIModelRepository(self.db)
            ai_model = await ai_model_repo.get_model_by_id(generation_model)
            
            if not ai_model:
                raise ValueError(f"未找到AI模型: {generation_model}")
            
            if not ai_model.is_enabled:
                raise ValueError(f"AI模型已禁用: {ai_model.name}")
            
            # 检查模型是否支持图片生成能力
            if 'image_gen' not in (ai_model.capabilities or []):
                raise ValueError(f"模型不支持图片生成能力: {ai_model.name}")
            
            # 获取provider名称
            provider_mapping = ai_model.provider_mapping or {}
            provider_name = provider_mapping.get('image_gen')
            
            if not provider_name:
                raise ValueError(f"模型未配置图片生成provider: {ai_model.name}")
            
            # 构建模型配置
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

            logger.info("创建AI图片生成Provider", extra={
                "provider_name": provider_name,
                "model_id": ai_model.id,
                "model_name": ai_model.ai_model_name
            })

            # 3. 使用AIProviderFactory创建provider
            image_gen_provider = AIProviderFactory.create_provider(
                capability=ModelCapability.IMAGE_GEN,
                provider_name=provider_name,
                model_config=model_config
            )

            if not image_gen_provider:
                raise ValueError(f"不支持的模型provider: {provider_name}")

            # 准备生成参数
            generation_params = {
                "prompt": prompt,
                "width": int(canvas_size["width"]),
                "height": int(canvas_size["height"]),
                "ref_images": [template_image_url],  # 使用模板作为参考图片
            }

            logger.info("调用AI Provider生成图片", extra={
                "provider_type": image_gen_provider.__class__.__name__,
                "model": ai_model.ai_model_name,
                "canvas_size": canvas_size
            })

            # 4. 执行图片生成
            result = await image_gen_provider.generate_image(**generation_params)

            if not result or not result.image:
                raise Exception("图片生成失败：返回结果为空")

            generation_time = time.time() - start_time

            logger.info("幻灯片图片生成成功", extra={
                "slide_index": slide_index,
                "generation_time": round(generation_time, 2),
                "image_size": result.image.size if result.image else None
            })

            return {
                "pil_image": result.image,
                "generation_time": generation_time,
                "prompt": prompt,
                "provider_response": getattr(result, 'raw_response', None)
            }

        except Exception as e:
            logger.error("幻灯片图片生成失败", extra={
                "slide_index": slide_index,
                "error": str(e),
                "exception_type": type(e).__name__
            })
            raise

    async def upload_image_to_cos(
        self,
        task_id: str,
        slide_index: int,
        image: Image.Image
    ) -> str:
        """
        上传图片到腾讯云COS（使用独立路径前缀）

        Args:
            task_id: 生成任务ID
            slide_index: 幻灯片索引
            image: PIL图片对象

        Returns:
            str: COS图片URL
        """
        import io
        from qcloud_cos import CosConfig, CosS3Client

        logger.info("开始上传图片到腾讯云COS", extra={
            "task_id": task_id,
            "slide_index": slide_index
        })

        try:
            # 1. 初始化COS客户端
            cos_config = CosConfig(
                Region=settings.cos_region,
                SecretId=settings.cos_secret_id,
                SecretKey=settings.cos_secret_key,
                Token=None,
                Scheme='https'
            )
            cos_client = CosS3Client(cos_config)

            # 2. 将PIL图片转换为字节流
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', optimize=True)
            img_byte_arr.seek(0)

            # 3. 构建COS路径（使用独立路径前缀 ai-generated/ppt/）
            cos_path = self.build_cos_path(task_id, slide_index)

            # 4. 上传到COS
            response = cos_client.put_object(
                Bucket=settings.cos_bucket,
                Key=cos_path,
                Body=img_byte_arr.getvalue(),
                ContentType='image/png'
            )

            logger.debug("COS上传响应", extra={
                "cos_path": cos_path,
                "response": getattr(response, 'Response', {})
            })

            # 5. 构建COS URL
            cos_url = f"https://{settings.cos_bucket}.cos.{settings.cos_region}.myqcloud.com/{cos_path}"

            logger.info("图片上传成功", extra={
                "task_id": task_id,
                "slide_index": slide_index,
                "cos_path": cos_path,
                "cos_url": cos_url
            })

            return cos_url

        except Exception as e:
            logger.error("图片上传到COS失败", extra={
                "task_id": task_id,
                "slide_index": slide_index,
                "error": str(e),
                "exception_type": type(e).__name__
            })
            raise

    async def update_slide_result_in_redis(
        self,
        redis_client,
        task_id: str,
        slide_index: int,
        generation_result: Dict[str, Any],
        cos_url: str
    ):
        """
        在Redis中更新幻灯片的生成结果

        Args:
            redis_client: Redis客户端
            task_id: 任务ID
            slide_index: 幻灯片索引
            generation_result: 生成结果
            cos_url: COS图片URL
        """
        task_manager = BananaTaskManager(redis_client)

        await task_manager.update_slide_status(
            task_id=task_id,
            slide_index=slide_index,
            status="completed",
            image_url=cos_url,
            generation_time=generation_result["generation_time"],
            cos_path=self.build_cos_path(task_id, slide_index),
            prompt=generation_result["prompt"]
        )

        logger.info("更新Redis中的幻灯片结果", extra={
            "task_id": task_id,
            "slide_index": slide_index,
            "cos_url": cos_url
        })
