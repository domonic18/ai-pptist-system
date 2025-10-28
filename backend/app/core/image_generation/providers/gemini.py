"""
Gemini图片生成提供商
支持通过OpenRouter API调用Gemini模型进行图片生成
"""

import json
import re
from typing import Optional, List, Dict, Any
import aiohttp
from app.core.log_utils import get_logger
from app.core.image_generation.base import BaseImageProvider, ImageGenerationResult

logger = get_logger(__name__)


class GeminiProvider(BaseImageProvider):
    """Gemini图片生成提供商"""

    # API配置常量
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 120
    DEFAULT_MAX_TOKENS = 4096

    # HTTP头信息
    HTTP_HEADERS = {
        "Content-Type": "application/json",
    }

    # 质量映射
    QUALITY_MAP = {
        "hd": "高质量",
        "standard": "标准质量"
    }

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "google/gemini-2.5-pro",
        "gemini-2.5-pro",
        "google/gemini-2.5-flash-image-preview",
        "gemini-2.5-flash-image-preview",
        "gemini-2.5",
        "google/gemini-2.5"
    ]

    def __init__(self, model_config):
        super().__init__(model_config)
        self.session = None

    async def _ensure_session(self):
        """确保aiohttp会话存在"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """通过OpenRouter调用Gemini进行对话式图片生成（由MLflow追踪调用）"""
        try:
            await self._ensure_session()

            self._validate_config()

            messages = self._build_messages(prompt, size, quality)
            request_payload = self._build_request_payload(messages)

            logger.info("调用OpenRouter Gemini图片生成", extra={
                "model": self.model_config.name,
                "prompt_length": len(prompt)
            })

            response_data = await self._call_openrouter_api(request_payload)

            if response_data:
                return self._handle_success_response(response_data, prompt, size, quality)
            else:
                return self._create_error_result("OpenRouter API调用失败")

        except aiohttp.ClientError as e:
            error_msg = f"OpenRouter网络连接错误: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)
        except Exception as e:
            error_msg = f"OpenRouter图片生成失败: {str(e)}"
            logger.error(error_msg, extra={"error": str(e)})
            return self._create_error_result(error_msg)

    def _validate_config(self):
        """验证配置"""
        if not hasattr(self.model_config, 'api_key') or not self.model_config.api_key:
            raise ValueError("OpenRouter API密钥未配置")

    def _build_messages(self, prompt: str, size: Optional[str], quality: Optional[str]) -> List[Dict]:
        """构建对话消息"""
        # 构建更明确的图片生成指令，确保模型返回图片
        text_content = (
            f"IMPORTANT: You are an image generation model. You MUST generate an image based on the following description. "
            f"DO NOT provide text explanations, suggestions, or alternative ideas. "
            f"Your response should ONLY contain the generated image as base64 data or image URL.\n\n"
            f"Image generation prompt: {prompt}"
        )

        if size:
            text_content += f"\nSize requirement: {size}"
        if quality:
            quality_text = self.QUALITY_MAP.get(quality, quality)
            text_content += f"\nQuality: {quality_text}"

        # 添加系统消息来明确指示模型行为
        system_message = {
            "role": "system",
            "content": "You are an image generation assistant. Your ONLY task is to generate images based on user prompts. "
                       "You MUST respond with image data (base64 encoded or URL) and NEVER with text explanations, "
                       "suggestions, or alternative ideas. If you cannot generate an image, respond with an error message "
                       "starting with 'ERROR:' followed by the reason."
        }

        user_message = {
            "role": "user",
            "content": [{"type": "text", "text": text_content}]
        }

        return [system_message, user_message]

    def _build_request_payload(self, messages: List[Dict]) -> Dict:
        """构建API请求负载"""
        return {
            "model": self.model_config.name,
            "messages": messages,
            "max_tokens": self.DEFAULT_MAX_TOKENS
        }

    async def _call_openrouter_api(self, request_payload: Dict) -> Optional[Dict]:
        """调用OpenRouter API"""
        headers = self._build_headers()

        async with self.session.post(
            f"{self.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=request_payload
        ) as response:

            if response.status == 200:
                response_data = await response.json()
                logger.info("OpenRouter API响应结构", extra={
                    "choices_count": len(response_data.get("choices", [])),
                    "message_keys": list(response_data.get("choices", [{}])[0].get("message", {}).keys()) if response_data.get("choices") else []
                })
                return response_data
            else:
                error_text = await response.text()
                logger.error("OpenRouter API错误", extra={
                    "status": response.status,
                    "error": error_text
                })
                return None

    def _build_headers(self) -> Dict:
        """构建HTTP头信息"""
        headers = self.HTTP_HEADERS.copy()
        headers["Authorization"] = f"Bearer {self.model_config.api_key}"
        return headers

    def _handle_success_response(self, response_data: Dict, prompt: str, size: str, quality: str) -> ImageGenerationResult:
        """处理成功响应"""
        image_url = self._extract_image_url(response_data)

        if image_url:
            logger.info("OpenRouter Gemini图片生成成功")

            metadata = self._extract_metadata(response_data, {
                "prompt": prompt,
                "size": size,
                "quality": quality
            })

            return ImageGenerationResult(
                success=True,
                image_url=image_url,
                metadata=metadata
            )
        else:
            # 检查响应内容，提供更具体的错误信息
            error_msg = self._analyze_response_for_errors(response_data)
            if not error_msg:
                error_msg = "OpenRouter Gemini模型返回了文本响应而不是图片数据。模型可能没有遵循图片生成指令。"

            logger.warning("OpenRouter图片生成失败", extra={"error": error_msg})
            return self._create_error_result(error_msg)

    def _analyze_response_for_errors(self, response_data: Dict) -> str:
        """分析响应内容，提取具体的错误信息"""
        try:
            if not (response_data.get("choices") and len(response_data["choices"]) > 0):
                return "API响应中没有包含有效的数据"

            choice = response_data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")

            if content.startswith('ERROR:'):
                return f"模型返回错误: {content[6:]}"

            if isinstance(content, str) and len(content) > 100:
                # 检查是否包含拒绝生成图片的文本
                refusal_keywords = ['cannot', 'unable', 'sorry', 'apologize', 'not allowed', 'against', 'policy']
                if any(keyword in content.lower() for keyword in refusal_keywords):
                    return "模型拒绝生成图片，可能由于内容政策限制"

                # 检查是否提供了文本解释而不是图片
                if 'explain' in content.lower() or 'suggest' in content.lower():
                    return "模型提供了文本解释而不是生成图片"

            return ""

        except Exception as e:
            logger.warning("分析响应错误时发生异常", extra={"error": str(e)})
            return "无法解析API响应内容"

    def _create_error_result(self, error_message: str) -> ImageGenerationResult:
        """创建错误结果"""
        return ImageGenerationResult(
            success=False,
            error_message=error_message
        )

    def _extract_image_url(self, response_data: Dict[str, Any]) -> Optional[str]:
        """从OpenRouter响应中提取图片URL或base64编码的图片数据"""
        try:
            if not (response_data.get("choices") and len(response_data["choices"]) > 0):
                logger.debug("响应中没有choices字段或choices为空")
                return None

            choice = response_data["choices"][0]
            message = choice.get("message", {})

            logger.info("解析message字段内容", extra={
                "message_preview": json.dumps(message, ensure_ascii=False)[:1000],
                "message_type": type(message.get("content", "")).__name__
            })

            # 详细记录content内容以便调试
            content = message.get("content")
            if isinstance(content, str):
                logger.info("检测到字符串类型content", extra={
                    "content_length": len(content),
                    "content_preview": content[:500]
                })
            elif isinstance(content, list):
                logger.info("检测到列表类型content", extra={
                    "content_length": len(content),
                    "content_types": [type(item).__name__ for item in content]
                })
            else:
                logger.info("检测到其他类型content", extra={
                    "content_type": type(content).__name__ if content else "None"
                })

            # 优先检查images字段
            image_url = self._extract_from_images_field(message)
            if image_url:
                logger.debug("从images字段找到图片URL", extra={"url_preview": image_url[:100]})
                return image_url

            # 检查content字段
            image_url = self._extract_from_content_field(message)
            if image_url:
                logger.debug("从content字段找到图片URL", extra={"url_preview": image_url[:100]})
                return image_url

            logger.debug("未在响应中找到图片URL")
            return None

        except Exception as e:
            logger.warning("提取图片URL失败", extra={"error": str(e)})
            return None

    def _extract_from_images_field(self, message: Dict) -> Optional[str]:
        """从images字段提取图片URL"""
        if not (message.get("images") and isinstance(message["images"], list)):
            return None

        for image_item in message["images"]:
            if not isinstance(image_item, dict):
                continue

            image_url_data = image_item.get("image_url")
            if not image_url_data:
                continue

            return self._process_image_url_data(image_url_data)

        return None

    def _extract_from_content_field(self, message: Dict) -> Optional[str]:
        """从content字段提取图片URL"""
        content = message.get("content")
        if not content:
            return None

        if isinstance(content, str):
            return self._extract_from_string_content(content)
        elif isinstance(content, list):
            return self._extract_from_list_content(content)

        return None

    def _extract_from_string_content(self, content: str) -> Optional[str]:
        """从字符串内容中提取图片URL"""
        # 首先检查是否有错误消息
        if content.startswith('ERROR:'):
            logger.warning("模型返回错误消息", extra={"content": content})
            return None

        # 检查是否包含文本解释而不是图片（模型没有遵循指令）
        if len(content) > 200 and not any(keyword in content.lower() for keyword in ['data:image', 'http', 'base64']):
            logger.warning("模型返回了文本解释而不是图片数据", extra={"content_preview": content[:200]})
            return None

        # 尝试解析为JSON
        try:
            content_data = json.loads(content)
            if isinstance(content_data, dict):
                image_url = content_data.get("image_url")
                if image_url:
                    return self._process_image_url_data(image_url)
        except json.JSONDecodeError:
            pass

        # 查找base64编码的图片数据 - 更全面的匹配
        base64_matches = re.findall(r'data:image\/[^;]+;base64,[^\s\"]+', content)
        if base64_matches:
            logger.info("找到base64图片数据", extra={"count": len(base64_matches)})
            return base64_matches[0]

        # 查找独立的base64字符串（可能没有data:image前缀）
        # 检查是否有大段的base64编码内容
        import base64 as b64
        base64_blocks = re.findall(r'[A-Za-z0-9+/]{100,}={0,2}', content)
        for block in base64_blocks:
            # 尝试解码验证是否为有效的base64
            try:
                decoded = b64.b64decode(block + '==')  # 添加padding
                # 检查解码后的内容是否为图片格式
                if decoded.startswith(b'\xFF\xD8\xFF'):  # JPEG
                    logger.info("检测到JPEG base64数据")
                    return f"data:image/jpeg;base64,{block}"
                elif decoded.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                    logger.info("检测到PNG base64数据")
                    return f"data:image/png;base64,{block}"
                elif decoded.startswith(b'GIF87a') or decoded.startswith(b'GIF89a'):  # GIF
                    logger.info("检测到GIF base64数据")
                    return f"data:image/gif;base64,{block}"
                elif decoded.startswith(b'RIFF') and b'WEBP' in decoded:  # WebP
                    logger.info("检测到WebP base64数据")
                    return f"data:image/webp;base64,{block}"
            except Exception:
                continue

        # 查找普通URL
        urls = re.findall(r'https?:\/\/[^\s\"]+\.(?:jpg|jpeg|png|gif|webp)', content, re.IGNORECASE)
        if urls:
            logger.info("找到普通图片URL", extra={"count": len(urls)})
            return urls[0]

        # 查找通用的图片URL（没有扩展名但可能是图片）
        image_urls = re.findall(r'https?:\/\/[^\s\"]+', content)
        for url in image_urls:
            # 检查URL是否看起来像图片（包含常见图片路径关键词）
            if any(keyword in url.lower() for keyword in ['image', 'img', 'picture', 'photo', 'cdn', 'storage']):
                logger.info("找到通用图片URL", extra={"url": url[:100]})
                return url

        # 如果都没找到，记录完整的响应内容用于调试
        logger.info("未找到任何图片格式，记录完整响应", extra={
            "full_content": content[:1000] if len(content) > 1000 else content
        })

        return None

    def _extract_from_list_content(self, content: List) -> Optional[str]:
        """从列表内容中提取图片URL"""
        logger.info("开始解析列表内容", extra={"item_count": len(content)})

        for i, item in enumerate(content):
            logger.info("解析列表项", extra={"item_index": i, "item_type": type(item).__name__})

            if not isinstance(item, dict):
                # 如果是字符串，尝试直接解析
                if isinstance(item, str):
                    logger.info("列表项为字符串，尝试解析图片", extra={"preview": item[:200]})
                    result = self._extract_from_string_content(item)
                    if result:
                        return result
                continue

            # 记录字典的所有键以便调试
            logger.info("列表项为字典，记录所有字段", extra={"keys": list(item.keys())})

            # 检查image_url字段
            image_url = item.get("image_url")
            if image_url:
                logger.info("找到image_url字段")
                result = self._process_image_url_data(image_url)
                if result:
                    return result

            # 检查url字段
            url = item.get("url")
            if url and isinstance(url, str):
                logger.info("找到url字段")
                result = self._process_image_url_data(url)
                if result:
                    return result

            # 检查text字段是否包含图片信息
            text_field = item.get("text")
            if text_field and isinstance(text_field, str):
                logger.info("找到text字段，尝试解析图片", extra={"preview": text_field[:200]})
                result = self._extract_from_string_content(text_field)
                if result:
                    return result

            # 检查content字段（嵌套结构）
            nested_content = item.get("content")
            if nested_content:
                if isinstance(nested_content, str):
                    logger.info("找到嵌套content字段（字符串）", extra={"preview": nested_content[:200]})
                    result = self._extract_from_string_content(nested_content)
                    if result:
                        return result
                elif isinstance(nested_content, list):
                    logger.info("找到嵌套content字段（列表），递归解析")
                    result = self._extract_from_list_content(nested_content)
                    if result:
                        return result

        return None

    def _process_image_url_data(self, image_url_data: Any) -> Optional[str]:
        """处理图片URL数据"""
        if isinstance(image_url_data, dict):
            url_value = image_url_data.get("url")
            if url_value and isinstance(url_value, str):
                return self._validate_and_return_url(url_value)
        elif isinstance(image_url_data, str):
            return self._validate_and_return_url(image_url_data)

        return None

    def _validate_and_return_url(self, url: str) -> Optional[str]:
        """验证并返回有效的URL"""
        if url.startswith("data:image/") or url.startswith("http"):
            return url
        return None

    def _extract_metadata(self, response_data: Dict[str, Any], api_params: Dict[str, Any]) -> Dict[str, Any]:
        """提取OpenRouter响应元数据"""
        metadata = {
            'provider': 'openrouter',
            'model': self.model_config.name,
            'prompt': api_params.get('prompt'),
            'size': api_params.get('size'),
            'quality': api_params.get('quality')
        }

        # 添加OpenRouter特定的元数据
        if response_data.get("id"):
            metadata['request_id'] = response_data["id"]
        if response_data.get("created"):
            metadata['created'] = response_data["created"]
        if response_data.get("usage"):
            metadata['usage'] = response_data["usage"]

        return metadata

    def supports_model(self, model_name: str) -> bool:
        """检查是否支持指定的模型"""
        return model_name.lower() in [model.lower() for model in self.SUPPORTED_MODELS]

    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return self.SUPPORTED_MODELS.copy()

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸列表"""
        return [
            "1024x1024",
            "1792x1024",
            "1024x1792",
            "512x512",
            "768x768",
            "1024x768",
            "768x1024"
        ]

    def get_supported_qualities(self) -> List[str]:
        """获取支持的图片质量列表"""
        return ["standard", "hd"]

    def validate_config(self) -> bool:
        """验证配置是否完整"""
        required_fields = ['api_key', 'name']
        for field in required_fields:
            if not hasattr(self.model_config, field) or not getattr(self.model_config, field):
                return False
        return True

    def __del__(self):
        """析构函数，确保会话关闭"""
        if self.session:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    asyncio.run(self.close())
            except:
                pass