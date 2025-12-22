"""
Banana幻灯片生成器
负责调用AI Provider生成单张幻灯片的图片
"""

import time
from typing import Dict, Any, Optional
from PIL import Image
from app.core.ai.factory import AIProviderFactory
from app.services.generation.banana_task_manager import BananaTaskManager
from app.core.config import settings
from app.core.log_utils import get_logger
from .banana_prompt_service import BananaPromptService

logger = get_logger(__name__)


class BananaSlideGenerator:
    """Banana幻灯片图片生成器"""

    def __init__(self):
        """初始化生成器"""
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
        canvas_size: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        生成单张幻灯片图片

        Args:
            slide_index: 幻灯片索引
            slide_data: 幻灯片数据（包含title和points）
            template_image_url: 模板图片URL
            generation_model: 生成模型名称
            canvas_size: 画布尺寸 {width, height}

        Returns:
            Dict: 生成结果，包含pil_image、generation_time等
        """
        start_time = time.time()
        logger.info("开始生成幻灯片图片", extra={
            "slide_index": slide_index,
            "slide_title": slide_data.get("title")
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

            # 2. 调用AI Provider生成图片
            factory = AIProviderFactory()
            provider = factory.get_provider(generation_model)

            if not provider:
                raise ValueError(f"无法找到指定的AI模型: {generation_model}")

            # 准备生成参数
            generation_params = {
                "prompt": prompt,
                "width": canvas_size["width"],
                "height": canvas_size["height"],
                "size": f"{canvas_size['width']}x{canvas_size['height']}",
                "ref_images": [template_image_url],  # 使用模板作为参考图片
                "model": generation_model
            }

            logger.info("调用AI Provider生成图片", extra={
                "provider_type": provider.__class__.__name__,
                "model": generation_model,
                "canvas_size": canvas_size
            })

            # 3. 执行图片生成
            result = await provider.generate_image(**generation_params)

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
