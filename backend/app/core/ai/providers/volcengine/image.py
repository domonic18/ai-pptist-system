"""
火山引擎豆包文生图 Provider

豆包 API 文档: https://www.volcengine.com/docs/82379/1541523?lang=zh
支持通过 image 参数传递参考图URL
"""

from typing import Optional, List, Any
import io
import base64
from PIL import Image
import httpx

from app.core.log_utils import get_logger
from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin
from app.core.ai.providers.openai_compatible.utils import (
    create_openai_client,
    handle_openai_exception
)

logger = get_logger(__name__)


class VolcengineImageProvider(BaseImageGenProvider, MLflowTracingMixin):
    """火山引擎豆包文生图 Provider"""

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "doubao-seedream-4-5",
        # 可扩展其他豆包模型
    ]

    # 豆包尺寸格式
    SIZE_FORMATS = {
        "2K": (1920, 1080),
        "4K": (3840, 2160),
    }

    def __init__(self, model_config):
        """
        初始化 Provider

        Args:
            model_config: AI模型配置对象
        """
        # 初始化基类
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)

        # API配置
        self.api_key = model_config.api_key
        self.base_url = getattr(
            model_config,
            'base_url',
            'https://ark.cn-beijing.volces.com/api/v3'
        )

        # 模型名称
        self.model = getattr(model_config, 'model_name', 'doubao-seedream-4-5')

        # 创建 OpenAI 客户端（豆包 API 兼容 OpenAI SDK）
        self.client = create_openai_client(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 验证模型
        if self.model not in self.SUPPORTED_MODELS:
            logger.warning(
                f"模型 {self.model} 可能不在支持列表中",
                operation="model_warning",
                model=self.model,
                supported_models=self.SUPPORTED_MODELS
            )

        logger.info(
            "火山引擎豆包图片生成客户端初始化完成",
            operation="volcengine_init",
            base_url=self.base_url,
            model=self.model
        )

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "volcengine"

    async def close(self):
        """关闭 OpenAI 客户端"""
        if hasattr(self, 'client') and self.client:
            await self.client.close()
            logger.debug("火山引擎 OpenAI 客户端已关闭")

    def _map_size_to_format(self, width: int, height: int) -> str:
        """
        映射尺寸到豆包格式（2K 或 4K）

        Args:
            width: 图片宽度
            height: 图片高度

        Returns:
            豆包尺寸格式："2K" 或 "4K"
        """
        if width >= 3840 or height >= 2160:
            return "4K"
        return "2K"

    def _extract_ref_image_url(self, ref_images: List[Any]) -> Optional[str]:
        """
        提取参考图 URL（只支持 HTTP/HTTPS 格式）

        Args:
            ref_images: 参考图列表

        Returns:
            第一个有效的 HTTP/HTTPS URL，如果没有则返回 None
        """
        if not ref_images:
            return None

        for ref_img in ref_images:
            if isinstance(ref_img, str):
                if ref_img.startswith('http://') or ref_img.startswith('https://'):
                    return ref_img

        return None

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        _quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸（豆包使用 2K/4K 格式，会被自动映射）
            _quality: 图片质量（豆包不支持此参数）
            **kwargs: 其他参数，包括：
                - width: 图片宽度
                - height: 图片高度
                - ref_images: 参考图列表

        Returns:
            ImageGenerationResult: 图片生成结果
        """
        try:
            # 参数处理
            width = kwargs.get('width', 1920)
            height = kwargs.get('height', 1080)
            ref_images = kwargs.get('ref_images', [])

            # 尺寸映射到豆包格式
            size_format = self._map_size_to_format(width, height)

            # 准备 extra_body（豆包特定参数）
            extra_body = {
                "watermark": False  # 不添加水印
            }

            # 处理参考图
            ref_image_url = self._extract_ref_image_url(ref_images)

            if ref_image_url:
                extra_body["image"] = ref_image_url
                logger.info(
                    "调用火山引擎豆包图片生成API（带参考图）",
                    operation="volcengine_image_start",
                    model=self.model,
                    size=size_format,
                    width=width,
                    height=height,
                    prompt_length=len(prompt),
                    prompt_preview=prompt[:200] if len(prompt) > 200 else prompt,
                    ref_image_url=ref_image_url
                )
            else:
                logger.info(
                    "调用火山引擎豆包图片生成API（无参考图）",
                    operation="volcengine_image_start",
                    model=self.model,
                    size=size_format,
                    width=width,
                    height=height,
                    prompt_length=len(prompt),
                    prompt_preview=prompt[:200] if len(prompt) > 200 else prompt,
                    ref_images_count=len(ref_images)
                )

            # 调用豆包的图片生成API
            # 使用 extra_body 传递豆包特定参数（watermark, image）
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size_format,
                extra_body=extra_body
            )

            # 处理响应
            if response.data and len(response.data) > 0:
                # 豆包返回的数据格式可能不同，需要兼容处理
                image_data = response.data[0]

                # 尝试获取URL
                image_url = getattr(image_data, 'url', None)

                if not image_url and hasattr(image_data, 'b64_json'):
                    # 如果是 base64 格式
                    image_url = f"data:image/png;base64,{image_data.b64_json}"

                if image_url:
                    pil_image = self._get_pil_image(image_url)
                    return ImageGenerationResult(
                        success=True,
                        image_url=image_url,
                        image=pil_image,
                        metadata={
                            "model": self.model,
                            "size": size_format,
                            "width": width,
                            "height": height
                        }
                    )

            return ImageGenerationResult(
                success=False,
                error_message="火山引擎豆包 API 未返回图片数据"
            )

        except Exception as e:
            base_url_str = str(self.client.base_url)
            error_msg = handle_openai_exception(e, base_url_str)
            logger.error(
                "火山引擎豆包API生成图片失败",
                operation="volcengine_image_error",
                model=self.model,
                error=str(e)
            )
            return ImageGenerationResult(success=False, error_message=error_msg)

    def _download_image_content(self, url: str) -> Optional[bytes]:
        """
        从 HTTP URL 下载图片内容

        Args:
            url: 图片 URL

        Returns:
            Optional[bytes]: 图片字节数据，失败返回 None
        """
        try:
            logger.info(
                "下载图片",
                operation="download_image",
                url=url[:100] if len(url) > 100 else url
            )

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()

                if len(response.content) < 100:
                    logger.warning(f"下载的图片数据过小: {len(response.content)} bytes")
                    return None

                return response.content
        except Exception as e:
            logger.error(
                f"下载图片失败: {e}",
                operation="download_image_failed",
                url=url[:100] if len(url) > 100 else url
            )
            return None

    def _get_pil_image(self, data: str) -> Optional[Image.Image]:
        """
        将图片数据（URL 或 base64）转换为 PIL Image 对象

        Args:
            data: 图片 URL 或 base64 数据

        Returns:
            Optional[Image.Image]: PIL Image 对象，失败返回 None
        """
        try:
            if data.startswith('http'):
                content = self._download_image_content(data)
                return Image.open(io.BytesIO(content)) if content else None
            elif data.startswith('data:image'):
                base64_data = data.split(',')[1] if ',' in data else data
                return Image.open(io.BytesIO(base64.b64decode(base64_data)))
            else:
                # 尝试作为纯 base64 处理
                return Image.open(io.BytesIO(base64.b64decode(data)))
        except Exception as e:
            logger.error(
                f"转换 PIL Image 失败: {e}",
                operation="pil_image_conversion_failed"
            )
            return None
