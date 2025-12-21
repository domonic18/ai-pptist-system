"""
OpenAI兼容图片生成提供商
支持OpenAI兼容的图片生成API
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
import openai
from app.core.log_utils import get_logger
from app.core.imggen.base import BaseImageProvider, ImageGenerationResult

logger = get_logger(__name__)


class OpenAICompatibleProvider(BaseImageProvider):
    """OpenAI兼容图片生成提供商"""

    # 常量定义
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_TIMEOUT = 60
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_SIZE = "1024x1024"
    DEFAULT_QUALITY = "standard"

    def __init__(self, model_config):
        super().__init__(model_config)
        self.client = self._create_client()

    def _create_client(self):
        """创建OpenAI客户端"""
        if not hasattr(self.model_config, 'api_key') or not self.model_config.api_key:
            raise ValueError("OpenAI API密钥未配置")

        base_url = getattr(self.model_config, 'base_url', self.DEFAULT_BASE_URL)

        # 清理base_url：去除前后空格
        if base_url:
            base_url = base_url.strip()

        # 确保base_url包含协议前缀
        if base_url and not base_url.startswith(('http://', 'https://')):
            # 如果没有协议前缀，默认使用https
            base_url = f"https://{base_url}"
            logger.warning("base_url缺少协议前缀，已自动添加https://")

        return openai.AsyncOpenAI(
            api_key=self.model_config.api_key,
            base_url=base_url,
            timeout=getattr(self.model_config, 'timeout', self.DEFAULT_TIMEOUT),
            max_retries=getattr(self.model_config, 'max_retries', self.DEFAULT_MAX_RETRIES)
        )

    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """实际生成图片 - OpenAI兼容实现（由MLflow追踪调用）"""
        try:
            # 准备API参数
            api_params = {
                'model': self.model_config.name,
                'prompt': prompt,
                'size': size or getattr(self.model_config, 'size', self.DEFAULT_SIZE),
                'quality': quality or getattr(self.model_config, 'quality', self.DEFAULT_QUALITY),
                'n': 1
            }

            # 添加其他可选参数
            if 'style' in kwargs:
                api_params['style'] = kwargs['style']

            logger.info("调用OpenAI兼容图片生成API", extra={
                "model": api_params['model'],
                "size": api_params['size'],
                "quality": api_params['quality']
            })

            # 调用OpenAI API
            response = await self.client.images.generate(**api_params)

            # 处理响应
            response_handler = OpenAICompatibleResponseHandler()
            image_url = response_handler.extract_image_url(response)

            if image_url:
                logger.info("OpenAI兼容图片生成成功", extra={"image_url_preview": image_url[:50]})

                metadata = response_handler.extract_metadata(response, api_params)

                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    metadata=metadata
                )

            error_msg = "OpenAI兼容API返回空数据"
            logger.warning("OpenAI兼容API返回空数据")
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

        except openai.APIConnectionError as e:
            error_msg = f"OpenAI兼容连接错误: {str(e)}"
            logger.error("OpenAI兼容连接错误", extra={"error": str(e)})
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

        except openai.RateLimitError as e:
            error_msg = f"OpenAI兼容限流错误: {str(e)}"
            logger.warning("OpenAI兼容限流错误", extra={"error": str(e)})
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

        except openai.APIStatusError as e:
            error_msg = f"OpenAI兼容API状态错误: {e.status_code} - {str(e)}"
            logger.error("OpenAI兼容API状态错误", extra={
                "status_code": e.status_code,
                "error": str(e)
            })
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"OpenAI兼容图片生成失败: {str(e)}"
            logger.error("OpenAI兼容图片生成失败", extra={"error": str(e)})
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

    def supports_model(self, model_name: str) -> bool:
        """检查是否支持OpenAI兼容模型"""
        return True  # OpenAI兼容模式支持所有模型

    def get_supported_models(self) -> List[str]:
        """获取支持的OpenAI兼容模型列表"""
        return [
            'dall-e-3',
            'dall-e-2'
        ]

    def validate_config(self) -> bool:
        """验证配置是否完整"""
        required_fields = ['api_key', 'name']
        for field in required_fields:
            if not hasattr(self.model_config, field) or not getattr(self.model_config, field):
                return False
        return True

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸列表"""
        return [
            "1024x1024",
            "1792x1024",
            "1024x1792",
            "512x512",
            "256x256"
        ]

    def get_supported_qualities(self) -> List[str]:
        """获取支持的图片质量列表"""
        return ["standard", "hd"]


class OpenAICompatibleResponseHandler:
    """OpenAI兼容响应处理器"""

    def extract_image_url(self, response: Any) -> Optional[str]:
        """提取OpenAI格式的图片URL"""
        if hasattr(response, 'data') and response.data and len(response.data) > 0:
            return response.data[0].url
        return None

    def extract_metadata(self, response: Any, api_params: Dict[str, Any]) -> Dict[str, Any]:
        """提取OpenAI格式的元数据"""
        metadata = {
            'size': api_params.get('size'),
            'quality': api_params.get('quality'),
            'model': api_params.get('model'),
            'provider': 'openai-compatible'
        }

        if hasattr(response, 'created') and response.created:
            metadata['created'] = response.created
        if hasattr(response, 'model') and response.model:
            metadata['model'] = response.model

        return metadata