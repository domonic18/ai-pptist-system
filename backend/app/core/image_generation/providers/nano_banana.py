"""
Nano Banana Pro (Gemini 3 Pro Image Preview) 图片生成提供商
基于 Google GenAI SDK 实现
支持参考图片的文生图功能
"""

from typing import Optional, List, Dict, Any
from PIL import Image
import io
import base64
import asyncio
from functools import partial

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

from app.core.image_generation.base import BaseImageProvider, ImageGenerationResult
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class NanoBananaProvider(BaseImageProvider):
    """Nano Banana Pro 图片生成提供商"""
    
    # 支持的模型
    SUPPORTED_MODELS = [
        "gemini-3-pro-image-preview",
        "google/gemini-3-pro-image-preview",
        "nano-banana-pro",
        "nano banana pro"
    ]
    
    # 支持的比例
    SUPPORTED_ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]
    
    # 支持的分辨率
    SUPPORTED_RESOLUTIONS = ["1K", "2K", "4K"]
    
    # 尺寸到比例的映射
    SIZE_TO_ASPECT_RATIO = {
        "1024x1024": "1:1",
        "1792x1024": "16:9",
        "1024x1792": "9:16",
        "1920x1080": "16:9",
        "1080x1920": "9:16",
        "2048x2048": "1:1",
        "3840x2160": "16:9",
        "2160x3840": "9:16",
    }
    
    def __init__(self, model_config):
        """
        初始化Nano Banana提供商
        
        Args:
            model_config: AI模型配置对象
                - api_key: Google API密钥
                - base_url: API基础URL（可选，用于代理）
                - name: 模型名称
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "Google GenAI SDK 未安装。请运行: pip install google-genai"
            )
        
        super().__init__(model_config)
        
        # 初始化Google GenAI客户端
        http_options = None
        if hasattr(model_config, 'base_url') and model_config.base_url:
            http_options = types.HttpOptions(base_url=model_config.base_url)
        
        self.client = genai.Client(
            api_key=model_config.api_key,
            http_options=http_options
        )
        
        # 模型名称（使用配置中的名称或默认值）
        self.model = getattr(model_config, 'ai_model_name', None) or getattr(model_config, 'name', 'gemini-3-pro-image-preview')
        
        logger.info(
            "NanoBananaProvider初始化成功",
            operation="provider_init_success",
            model=self.model,
            has_api_base=bool(http_options)
        )
    
    def _size_to_aspect_ratio(self, size: str) -> str:
        """
        将尺寸字符串转换为比例
        
        Args:
            size: 尺寸字符串，如 "1920x1080"
        
        Returns:
            str: 比例字符串，如 "16:9"
        """
        return self.SIZE_TO_ASPECT_RATIO.get(size, "16:9")
    
    def _process_reference_images(self, ref_images: List[Any]) -> List[Image.Image]:
        """
        处理参考图片，支持多种输入格式
        
        Args:
            ref_images: 参考图片列表，可以是 PIL.Image、文件路径、URL或base64编码
        
        Returns:
            List[Image.Image]: 处理后的PIL Image对象列表
        """
        processed_images = []
        
        for ref_img in ref_images:
            try:
                if isinstance(ref_img, Image.Image):
                    # 已经是PIL Image对象
                    processed_images.append(ref_img)
                elif isinstance(ref_img, str):
                    # 字符串类型：可能是文件路径、URL或base64编码
                    if ref_img.startswith('data:image'):
                        # base64编码的图片
                        base64_data = ref_img.split(',')[1] if ',' in ref_img else ref_img
                        image_data = base64.b64decode(base64_data)
                        processed_images.append(Image.open(io.BytesIO(image_data)))
                    elif ref_img.startswith('http://') or ref_img.startswith('https://'):
                        # URL - 这里需要下载（暂时跳过，由调用方处理）
                        logger.warning(
                            "URL参考图片需要预先下载",
                            operation="ref_image_skip_url",
                            url=ref_img[:100]
                        )
                    else:
                        # 假设是文件路径
                        processed_images.append(Image.open(ref_img))
                elif isinstance(ref_img, bytes):
                    # 字节数据
                    processed_images.append(Image.open(io.BytesIO(ref_img)))
                else:
                    logger.warning(
                        "不支持的参考图片类型",
                        operation="ref_image_unsupported_type",
                        type=type(ref_img).__name__
                    )
            except Exception as e:
                logger.error(
                    "处理参考图片失败",
                    operation="ref_image_process_error",
                    exception=e
                )
        
        return processed_images
    
    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片（内部实现）
        
        Args:
            prompt: 图片生成提示词
            size: 图片尺寸（格式：宽x高，如 "1920x1080"）
            quality: 图片质量（暂不支持，保留参数用于接口统一）
            **kwargs: 额外参数
                - ref_images: List[Any] 参考图片列表（PIL.Image、文件路径、URL或base64）
                - aspect_ratio: str 图片比例（如 "16:9"）
                - resolution: str 分辨率（如 "2K"）
        
        Returns:
            ImageGenerationResult: 生成结果
        """
        try:
            # 解析参数
            ref_images = kwargs.get('ref_images', [])
            aspect_ratio = kwargs.get('aspect_ratio', '16:9')
            resolution = kwargs.get('resolution', '2K')
            
            # 从size参数推导aspect_ratio（如果未提供）
            if size and not kwargs.get('aspect_ratio'):
                aspect_ratio = self._size_to_aspect_ratio(size)
            
            # 验证参数
            if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
                logger.warning(
                    f"不支持的比例 {aspect_ratio}，使用默认值 16:9",
                    operation="aspect_ratio_fallback"
                )
                aspect_ratio = "16:9"
            
            if resolution not in self.SUPPORTED_RESOLUTIONS:
                logger.warning(
                    f"不支持的分辨率 {resolution}，使用默认值 2K",
                    operation="resolution_fallback"
                )
                resolution = "2K"
            
            # 处理参考图片
            processed_ref_images = []
            if ref_images:
                processed_ref_images = self._process_reference_images(ref_images)
            
            # 构建生成内容
            contents = []
            
            # 添加参考图片（模板图）
            for ref_img in processed_ref_images:
                contents.append(ref_img)
            
            # 添加文本提示词
            contents.append(prompt)
            
            logger.info(
                "调用Gemini API生成图片",
                operation="api_call_start",
                model=self.model,
                prompt_length=len(prompt),
                ref_images_count=len(processed_ref_images),
                aspect_ratio=aspect_ratio,
                resolution=resolution
            )
            
            # 调用Google GenAI API（在线程池中执行，避免阻塞）
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE'],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=resolution
                        ),
                    )
                )
            )
            
            logger.debug(
                "Gemini API响应完成",
                operation="api_response_received",
                parts_count=len(response.parts) if response.parts else 0
            )
            
            # 提取图片
            for i, part in enumerate(response.parts):
                if part.text is not None:
                    logger.debug(
                        f"响应部分 {i}: 文本",
                        operation="response_part_text",
                        text_preview=part.text[:100] if len(part.text) > 100 else part.text
                    )
                else:
                    try:
                        image = part.as_image()
                        if image:
                            logger.info(
                                "成功提取图片",
                                operation="image_extracted",
                                part_index=i,
                                image_size=image.size
                            )
                            
                            # 将PIL Image转换为base64 data URL
                            buffered = io.BytesIO()
                            image.save(buffered, format="PNG")
                            img_base64 = base64.b64encode(buffered.getvalue()).decode()
                            image_url = f"data:image/png;base64,{img_base64}"
                            
                            return ImageGenerationResult(
                                success=True,
                                image_url=image_url,
                                metadata={
                                    "model": self.model,
                                    "aspect_ratio": aspect_ratio,
                                    "resolution": resolution,
                                    "prompt": prompt,
                                    "has_ref_images": len(processed_ref_images) > 0,
                                    "ref_images_count": len(processed_ref_images),
                                    "width": image.size[0],
                                    "height": image.size[1]
                                }
                            )
                    except Exception as e:
                        logger.error(
                            f"提取图片失败",
                            operation="image_extraction_error",
                            part_index=i,
                            exception=e
                        )
            
            # 如果没有找到图片
            error_msg = "API响应中未找到图片数据"
            logger.error(error_msg, operation="no_image_in_response")
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Nano Banana 图片生成失败: {str(e)}"
            logger.error(
                error_msg,
                operation="generation_failed",
                exception=e
            )
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )
    
    def supports_model(self, model_name: str) -> bool:
        """
        检查是否支持指定模型
        
        Args:
            model_name: 模型名称
        
        Returns:
            bool: 是否支持该模型
        """
        return any(
            supported_name.lower() in model_name.lower()
            for supported_name in self.SUPPORTED_MODELS
        )
    
    def get_supported_models(self) -> List[str]:
        """
        获取支持的模型列表
        
        Returns:
            List[str]: 支持的模型名称列表
        """
        return self.SUPPORTED_MODELS.copy()
    
    def get_supported_sizes(self) -> List[str]:
        """
        获取支持的图片尺寸列表
        
        Returns:
            List[str]: 支持的尺寸列表（对应aspect_ratio）
        """
        return [
            "1024x1024",  # 1:1
            "1792x1024",  # 16:9
            "1024x1792",  # 9:16
            "1920x1080",  # 16:9 - HD
            "2048x2048",  # 1:1 - 2K
            "3840x2160",  # 16:9 - 4K
        ]
    
    def get_supported_qualities(self) -> List[str]:
        """
        获取支持的图片质量列表
        
        Returns:
            List[str]: 支持的质量列表（实际通过resolution控制）
        """
        return self.SUPPORTED_RESOLUTIONS.copy()

