"""
OpenAI兼容图片生成Provider
支持通过 Chat Completions API 或标准 Images API 生成图片
支持参考图片（通过多模态 Chat API）
"""

from typing import Optional, List, Any
import io
import base64
from PIL import Image
import re

from app.core.log_utils import get_logger
from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin
from .utils import (
    create_openai_client,
    handle_openai_exception
)

logger = get_logger(__name__)


class OpenAICompatibleImageProvider(BaseImageGenProvider, MLflowTracingMixin):
    """OpenAI兼容图片生成Provider"""

    def __init__(self, model_config):
        """初始化Provider"""
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)

        # 创建OpenAI客户端
        self.client = create_openai_client(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )

        # 模型名称
        self.model = model_config.model_name
        
        # 是否强制使用 Chat API (默认为 True，因为用户提供的参考代码是 Chat API)
        self.use_chat_api = getattr(model_config, 'parameters', {}).get('use_chat_api', True)

        logger.info(
            "OpenAI兼容图片生成客户端初始化完成",
            operation="openai_compatible_image_init",
            base_url=model_config.base_url,
            model=self.model,
            use_chat_api=self.use_chat_api
        )

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "openai_compatible"

    async def close(self):
        """关闭 OpenAI 客户端"""
        if hasattr(self, 'client') and self.client:
            await self.client.close()
            logger.debug("OpenAI 客户端已关闭")

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        _quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片
        
        支持通过 Chat Completions API 生成（当包含参考图时）
        或者通过标准的 Images Generations API 生成
        """
        # 从 kwargs 中提取 ref_images，避免后续通过 **kwargs 传递时导致参数冲突
        ref_images = kwargs.pop('ref_images', [])
        
        # 如果有参考图，或者配置强制使用 Chat API，则使用 Chat API
        if ref_images or self.use_chat_api:
            return await self._generate_via_chat(prompt, ref_images, **kwargs)
        else:
            return await self._generate_via_standard_api(prompt, size, **kwargs)

    async def _generate_via_chat(
        self,
        prompt: str,
        ref_images: List[Any],
        **kwargs
    ) -> ImageGenerationResult:
        """通过 Chat Completions API 生成图片（支持参考图）"""
        try:
            # 准备消息内容
            content = []
            
            # 1. 添加参考图片
            for ref_img in ref_images:
                base64_img = self._process_image_to_base64(ref_img)
                if base64_img:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_img}"
                        }
                    })
            
            # 2. 添加文本提示（简化格式，直接使用原始 prompt）
            content.append({
                "type": "text",
                "text": prompt
            })
            
            messages = [{"role": "user", "content": content}]
            
            # 准备 extra_body（使用 modalities 指定返回图片）
            extra_body = {"modalities": ["image", "text"]}
            
            # 过滤掉不属于 chat completions API 的参数
            chat_kwargs = {}
            valid_chat_params = {
                'temperature', 'top_p', 'n', 'stream', 'stop', 'max_tokens', 
                'presence_penalty', 'frequency_penalty', 'logit_bias', 'user',
                'response_format', 'seed', 'tools', 'tool_choice'
            }
            for k, v in kwargs.items():
                if k in valid_chat_params:
                    chat_kwargs[k] = v

            logger.info(
                "调用 OpenAI 兼容 Chat API 生成图片",
                operation="openai_chat_image_start",
                model=self.model,
                ref_images_count=len(ref_images)
            )

            # 调用 API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_body=extra_body,
                **chat_kwargs
            )
            
            # 提取图片数据
            message = response.choices[0].message
            
            # 1. 优先从 images 字段提取（OpenRouter 标准格式）
            image_data = self._extract_image_from_message(message)
            if image_data:
                image_url = self._prepare_image_url(image_data)
                pil_image = self._get_pil_image(image_url)
                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    image=pil_image,
                    metadata={"model": self.model, "method": "chat_images_field"}
                )

            # 2. 兼容：从 content 提取 Markdown 格式的图片链接
            content_text = message.content or ""
            image_url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content_text)
            if image_url_match:
                image_url = image_url_match.group(1)
                pil_image = self._get_pil_image(image_url)
                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    image=pil_image,
                    metadata={"model": self.model, "method": "chat_markdown"}
                )
            
            # 3. 兼容：检查 content 本身是否为 base64 编码的图片
            if len(content_text) > 500 and self._is_base64(content_text[:100]):
                image_url = self._prepare_image_url(content_text)
                pil_image = self._get_pil_image(image_url)
                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    image=pil_image,
                    metadata={"model": self.model, "method": "chat_content_base64"}
                )
            
            # 如果都没有找到图片，返回错误
            return ImageGenerationResult(
                success=False, 
                error_message=f"API未返回图片数据。响应预览: {content_text[:200] if content_text else '(空)'}"
            )

        except Exception as e:
            error_msg = handle_openai_exception(e, self.client.base_url)
            logger.error("Chat生成图片失败", operation="openai_chat_image_error", error=str(e))
            return ImageGenerationResult(success=False, error_message=error_msg)

    async def _generate_via_standard_api(
        self,
        prompt: str,
        size: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """通过标准的 Images Generations API 生成图片"""
        try:
            # 过滤掉不属于 images generations API 的参数
            img_kwargs = {}
            valid_img_params = {'n', 'quality', 'response_format', 'style', 'user'}
            for k, v in kwargs.items():
                if k in valid_img_params:
                    img_kwargs[k] = v

            logger.info(
                "调用 OpenAI 兼容标准 Images API 生成图片",
                operation="openai_standard_image_start",
                model=self.model,
                size=size
            )
            
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                **img_kwargs
            )
            
            if response.data and response.data[0].url:
                image_url = response.data[0].url
                pil_image = self._get_pil_image(image_url)
                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    image=pil_image,
                    metadata={"model": self.model, "method": "standard_api"}
                )
            
            return ImageGenerationResult(success=False, error_message="标准 API 未返回图片 URL")

        except Exception as e:
            error_msg = handle_openai_exception(e, self.client.base_url)
            logger.error("标准API生成图片失败", operation="openai_standard_image_error", error=str(e))
            return ImageGenerationResult(success=False, error_message=error_msg)

    def _is_base64(self, s: str) -> bool:
        """检查字符串是否可能是 base64 编码"""
        if not s or not isinstance(s, str):
            return False
        # base64 字符集：A-Z, a-z, 0-9, +, /, =
        return bool(re.match(r'^[A-Za-z0-9+/]*={0,2}$', s))

    def _download_image_content(self, url: str) -> Optional[bytes]:
        """
        从 HTTP URL 下载图片内容
        
        Args:
            url: 图片 URL
            
        Returns:
            Optional[bytes]: 图片字节数据，失败返回 None
        """
        import httpx
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
            logger.error(f"下载图片失败: {e}", url=url[:100] if len(url) > 100 else url)
            return None

    def _get_pil_image(self, data: str) -> Optional[Image.Image]:
        """
        将图片数据（URL 或 base64）转换为 PIL Image 对象
        """
        try:
            if data.startswith('http'):
                content = self._download_image_content(data)
                return Image.open(io.BytesIO(content)) if content else None
            elif data.startswith('data:image'):
                base64_data = data.split(',')[1] if ',' in data else data
                return Image.open(io.BytesIO(base64.b64decode(base64_data)))
            elif self._is_base64(data):
                return Image.open(io.BytesIO(base64.b64decode(data)))
            return None
        except Exception as e:
            logger.error(f"转换 PIL Image 失败: {e}")
            return None

    def _download_and_encode_image(self, url: str) -> Optional[str]:
        """
        从 HTTP URL 下载图片并转换为 base64
        """
        content = self._download_image_content(url)
        return base64.b64encode(content).decode() if content else None

    def _process_image_to_base64(self, img: Any) -> Optional[str]:
        """将图片对象转换为 base64 字符串"""
        try:
            if isinstance(img, Image.Image):
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode()
            elif isinstance(img, str):
                if img.startswith('data:image'):
                    return img.split(',')[1] if ',' in img else img
                elif img.startswith('http'):
                    # 下载 HTTP URL 图片并转换为 base64
                    return self._download_and_encode_image(img)
                else:
                    # 假设是文件路径
                    with open(img, "rb") as image_file:
                        return base64.b64encode(image_file.read()).decode()
            elif isinstance(img, bytes):
                return base64.b64encode(img).decode()
            return None
        except Exception as e:
            logger.error(f"处理参考图片为base64失败: {e}")
            return None

    def _extract_image_from_message(self, message: Any) -> Optional[str]:
        """从消息对象的各种字段中尝试提取图片数据"""
        # 1. 优先检查标准的 images 列表 (OpenRouter 官方格式)
        # 格式：response.images[0]['image_url']['url']
        images = getattr(message, 'images', None)
        if images and isinstance(images, list) and len(images) > 0:
            img_item = images[0]
            
            # 处理字典格式：image['image_url']['url']
            if isinstance(img_item, dict):
                # 标准格式
                image_url_obj = img_item.get('image_url')
                if image_url_obj and isinstance(image_url_obj, dict):
                    url = image_url_obj.get('url')
                    if url:
                        logger.info(
                            "从 images 字段提取到图片数据",
                            operation="extract_image_from_images",
                            data_length=len(url) if isinstance(url, str) else 0
                        )
                        return url
                
                # 兼容简化格式：{"url": "..."} 或 {"data": "..."}
                url = img_item.get('url') or img_item.get('data')
                if url:
                    logger.info(
                        "从 images 字段提取到图片数据（简化格式）",
                        operation="extract_image_from_images_simple",
                        data_length=len(url) if isinstance(url, str) else 0
                    )
                    return url
            
            # 处理字符串格式
            elif isinstance(img_item, str):
                logger.info(
                    "从 images 字段提取到图片数据（字符串格式）",
                    operation="extract_image_from_images_string",
                    data_length=len(img_item)
                )
                return img_item
        
        return None

    def _prepare_image_url(self, data: Any) -> str:
        """将原始数据处理为可用的 Data URL，并处理可能的包装头部"""
        if not isinstance(data, str):
            return ""
            
        if data.startswith('http'): 
            return data
        if data.startswith('data:image'): 
            return data
        
        try:
            # 针对 OpenRouter/Gemini 3 的特殊包装修复
            # 查找到 PNG 签名并截取，去除包装头部
            raw_bytes = base64.b64decode(data)
            png_sig = b'\x89PNG\r\n\x1a\n'
            idx = raw_bytes.find(png_sig)
            if idx != -1:
                clean_base64 = base64.b64encode(raw_bytes[idx:]).decode()
                return f"data:image/png;base64,{clean_base64}"
        except:
            pass
            
        return f"data:image/png;base64,{data}"

