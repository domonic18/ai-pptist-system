"""
Google GenAI (Gemini) 图片生成提供商
基于 Google GenAI SDK 实现
支持参考图片的文生图功能
"""

from typing import Optional, List, Any
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

from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class GenAIProvider(BaseImageGenProvider, MLflowTracingMixin):
    """Google GenAI 图片生成提供商"""
    
    # 支持的模型
    SUPPORTED_MODELS = [
        "gemini-3-pro-image-preview",
        "google/gemini-3-pro-image-preview",
        "gemini-2.0-flash-exp",
        "gemini-2.0-pro-exp"
    ]
    
    # 支持的比例
    SUPPORTED_ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
    
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
        初始化GenAI提供商
        
        Args:
            model_config: AI模型配置对象
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "Google GenAI SDK 未安装。请运行: pip install google-genai"
            )
        
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)
        
        # 初始化Google GenAI客户端
        # 根据用户提供的示例和参考代码进行配置
        api_base = getattr(model_config, 'base_url', None)
        http_options = None
        if api_base:
            # 统一使用字典格式，与用户提供的示例保持一致
            # 避免 types.HttpOptions 可能带来的额外默认逻辑
            http_options = {"base_url": api_base}

        self.client = genai.Client(
            api_key=model_config.api_key,
            http_options=http_options
        )
        
        # 模型名称
        self.model = getattr(model_config, 'ai_model_name', 'gemini-3-pro-image-preview')
        
        logger.info(
            "GenAIProvider初始化成功",
            operation="genai_init_success",
            model=self.model,
            has_api_base=bool(api_base)
        )
    
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "genai"
    
    def _size_to_aspect_ratio(self, size: str) -> str:
        """将尺寸字符串转换为比例"""
        return self.SIZE_TO_ASPECT_RATIO.get(size, "16:9")
    
    def _process_reference_images(self, ref_images: List[Any]) -> List[Image.Image]:
        """
        处理参考图片，支持多种输入格式
        
        Args:
            ref_images: 参考图片列表
        
        Returns:
            处理后的PIL Image对象列表
        """
        processed_images = []
        
        for ref_img in ref_images:
            try:
                if isinstance(ref_img, Image.Image):
                    processed_images.append(ref_img)
                elif isinstance(ref_img, str):
                    if ref_img.startswith('data:image'):
                        # base64编码的图片
                        base64_data = ref_img.split(',')[1] if ',' in ref_img else ref_img
                        image_data = base64.b64decode(base64_data)
                        processed_images.append(Image.open(io.BytesIO(image_data)))
                    elif ref_img.startswith('http://') or ref_img.startswith('https://'):
                        # 这里简单处理，实际上可能需要异步下载
                        logger.warning(
                            "URL参考图片需要预先下载，当前跳过",
                            operation="ref_image_skip_url",
                            url=ref_img[:100]
                        )
                    else:
                        # 文件路径
                        processed_images.append(Image.open(ref_img))
                elif isinstance(ref_img, bytes):
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
            prompt: 图片生成提示词
            size: 图片尺寸
            quality: 图片质量
            **kwargs: 额外参数
                - ref_images: List[Any] 参考图片列表
                - aspect_ratio: str 图片比例
                - resolution: str 分辨率
        
        Returns:
            ImageGenerationResult: 生成结果
        """
        try:
            # 解析参数
            ref_images = kwargs.get('ref_images', [])
            aspect_ratio = kwargs.get('aspect_ratio', '16:9')
            resolution = kwargs.get('resolution', '2K')
            
            # 从size参数推导aspect_ratio
            if size and not kwargs.get('aspect_ratio'):
                aspect_ratio = self._size_to_aspect_ratio(size)
            
            # 验证并格式化参数
            if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
                logger.warning(
                    f"不支持的比例 {aspect_ratio}，使用默认值 16:9",
                    operation="aspect_ratio_fallback"
                )
                aspect_ratio = "16:9"
            
            # 分辨率必须是大写 K
            if isinstance(resolution, str):
                resolution = resolution.upper()
                if not resolution.endswith('K'):
                    resolution = "2K"
            
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
            if not processed_ref_images:
                # 如果没有参考图，直接使用字符串，与用户示例一致
                contents = prompt
            else:
                # 有参考图时使用列表，参考图在前
                contents = []
                for ref_img in processed_ref_images:
                    contents.append(ref_img)
                contents.append(prompt)
            
            logger.info(
                "调用GenAI API生成图片",
                operation="genai_generate_start",
                model=self.model,
                prompt_length=len(prompt),
                ref_images_count=len(processed_ref_images),
                aspect_ratio=aspect_ratio,
                resolution=resolution
            )
            
            # 调用API
            loop = asyncio.get_event_loop()
            
            # 准备配置
            config = types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=resolution
                ),
            )

            response = await loop.run_in_executor(
                None,
                partial(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=config
                )
            )
            
            # 提取图片
            if not response.parts:
                return ImageGenerationResult(success=False, error_message="API响应中没有内容")
            
            for part in response.parts:
                # 跳过文本部分
                if part.text:
                    continue
                
                # 从 inline_data 获取图片字节数据
                if hasattr(part, 'inline_data') and part.inline_data:
                    try:
                        # 直接获取字节数据并用PIL打开
                        image = Image.open(io.BytesIO(part.inline_data.data))
                        
                        # 转换为 base64
                        buffered = io.BytesIO()
                        image.save(buffered, format="PNG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()
                        
                        logger.info("图片生成成功", operation="genai_image_success")
                        
                        return ImageGenerationResult(
                            success=True,
                            image_url=f"data:image/png;base64,{img_base64}",
                            metadata={
                                "model": self.model,
                                "prompt": prompt,
                                "aspect_ratio": aspect_ratio,
                                "resolution": resolution
                            }
                        )
                    except Exception as e:
                        logger.debug(f"提取图片失败: {str(e)}")
                        continue
            
            return ImageGenerationResult(success=False, error_message="响应中未包含图片数据")
            
        except Exception as e:
            error_msg = f"GenAI 图片生成错误: {str(e)}"
            logger.error(error_msg, operation="genai_generation_failed", exception=e)
            return ImageGenerationResult(success=False, error_message=error_msg)

