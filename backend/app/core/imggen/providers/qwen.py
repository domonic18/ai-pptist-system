"""
通义千问图片生成提供商
支持阿里云通义千问文生图API
"""

import time
import asyncio
from typing import Optional, List, Dict, Any
from app.core.log_utils import get_logger
from app.core.imggen.base import BaseImageProvider, ImageGenerationResult

logger = get_logger(__name__)


class QwenProvider(BaseImageProvider):
    """通义千问图片生成提供商"""

    # API配置常量
    DEFAULT_SIZE = "1328*1328"
    DEFAULT_TIMEOUT = 60

    # 尺寸映射 - 通义千问支持的尺寸
    SIZE_MAPPING = {
        "256x256": "1664*928",
        "512x512": "1472*1140",
        "1024x1024": "1328*1328",
        "1024x1792": "1140*1472",
        "1792x1024": "928*1664"
    }

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "qwen-image",
        "qwen-image-vl",
        "tongyi-image",
        "qwen-vl-max",
        "qwen-vl-plus"
    ]

    def __init__(self, model_config):
        super().__init__(model_config)
        self._client = None
        self._api_key = getattr(model_config, 'api_key', '')
        self._base_url = getattr(model_config, 'base_url', 'https://dashscope.aliyuncs.com/api/v1')

    async def _ensure_client(self):
        """确保客户端已初始化"""
        if self._client is None:
            await self._create_client()

    async def _create_client(self):
        """创建通义千问客户端"""
        try:
            # 这里需要导入dashscope SDK
            import dashscope
            from dashscope import MultiModalConversation

            if not self._api_key:
                raise ValueError("通义千问API密钥未配置")

            # 配置API密钥
            dashscope.api_key = self._api_key

            # 创建客户端会话
            self._client = MultiModalConversation

            logger.info("通义千问客户端初始化成功", extra={
                "model": self.model_config.name,
                "base_url": self._base_url
            })

        except ImportError as e:
            error_msg = f"通义千问SDK未安装，请安装: pip install dashscope - {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"通义千问客户端初始化失败: {str(e)}"
            logger.error(error_msg, extra={"error": str(e)})
            raise ValueError(error_msg)

    async def close(self):
        """关闭客户端"""
        self._client = None

    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """实际生成图片 - 通义千问实现（由MLflow追踪调用）"""
        try:
            await self._ensure_client()

            if not self._client:
                return self._create_error_result("通义千问客户端未初始化")

            # 准备API参数
            final_size = self._convert_size(size)

            logger.info("调用通义千问图片生成", extra={
                "model": self.model_config.name,
                "prompt_length": len(prompt),
                "size": final_size,
                "quality": quality
            })

            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._sync_generate_image,
                prompt, final_size, kwargs
            )

            # 处理响应
            image_url = self._extract_image_url(response)

            if image_url:
                logger.info("通义千问图片生成成功", extra={
                    "image_url_preview": image_url[:50]
                })

                metadata = self._extract_metadata(response, {
                    "model": self.model_config.name,
                    "size": final_size,
                    "quality": quality,
                    "prompt": prompt
                })

                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    metadata=metadata
                )
            else:
                error_msg = self._analyze_response_for_errors(response)
                if not error_msg:
                    error_msg = "通义千问API返回空数据"

                logger.warning("通义千问图片生成失败", extra={
                    "error": error_msg,
                    "response_preview": str(response)[:200]
                })

                return self._create_error_result(error_msg)

        except Exception as e:
            error_msg = f"通义千问图片生成失败: {str(e)}"
            logger.error(error_msg, extra={"error": str(e)})
            return self._create_error_result(error_msg)

    def _sync_generate_image(self, prompt: str, size: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """同步调用通义千问API"""
        try:
            from dashscope import MultiModalConversation

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]

            # 调用API
            response = MultiModalConversation.call(
                model=self.model_config.name,
                messages=messages,
                result_format='message',
                stream=False,
                watermark=kwargs.get('watermark', False),
                prompt_extend=kwargs.get('prompt_extend', True),
                negative_prompt=kwargs.get('negative_prompt', ''),
                size=size
            )

            return response

        except Exception as e:
            logger.error("同步调用通义千问API失败", extra={"error": str(e)})
            raise

    def _convert_size(self, size: Optional[str]) -> str:
        """转换尺寸格式为通义千问支持的格式"""
        if not size:
            return self.DEFAULT_SIZE

        # 如果已经是通义千问格式，直接返回
        if '*' in size:
            return size

        # 转换OpenAI格式到通义千问格式
        return self.SIZE_MAPPING.get(size, self.DEFAULT_SIZE)

    def _extract_image_url(self, response: Dict[str, Any]) -> Optional[str]:
        """提取通义千问格式的图片URL"""
        try:
            # SDK响应格式: output.choices[0].message.content[0].image
            if (response.get('output') and
                response['output'].get('choices') and
                len(response['output']['choices']) > 0 and
                response['output']['choices'][0].get('message') and
                response['output']['choices'][0]['message'].get('content') and
                len(response['output']['choices'][0]['message']['content']) > 0):

                content = response['output']['choices'][0]['message']['content'][0]
                if content.get('image'):
                    return content['image']

            return None

        except Exception as e:
            logger.warning("提取通义千问图片URL失败", extra={"error": str(e)})
            return None

    def _extract_metadata(self, response: Dict[str, Any], api_params: Dict[str, Any]) -> Dict[str, Any]:
        """提取通义千问格式的元数据"""
        metadata = {
            'provider': 'qwen',
            'model': api_params.get('model'),
            'size': api_params.get('size'),
            'quality': api_params.get('quality'),
            'created': int(time.time())
        }

        # 添加通义千问特定的元数据
        if response.get('request_id'):
            metadata['request_id'] = response['request_id']
        if response.get('usage'):
            metadata['usage'] = response['usage']

        return metadata

    def _analyze_response_for_errors(self, response: Dict[str, Any]) -> str:
        """分析响应中的错误信息"""
        try:
            if not response:
                return "空响应"

            # 检查是否有错误信息
            if response.get('code'):
                return f"API错误: {response.get('message', '未知错误')}"

            # 检查是否有拒绝生成的内容
            if response.get('output', {}).get('choices'):
                choice = response['output']['choices'][0]
                message = choice.get('message', {})
                content = message.get('content', [])

                if content and isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and 'text' in first_content:
                        text = first_content['text']
                        if any(keyword in text.lower() for keyword in ['cannot', 'unable', 'sorry', 'apologize']):
                            return "模型拒绝生成图片，可能由于内容政策限制"

            return ""

        except Exception as e:
            logger.warning("分析通义千问响应错误时发生异常", extra={"error": str(e)})
            return "无法解析API响应内容"

    def _create_error_result(self, error_message: str) -> ImageGenerationResult:
        """创建错误结果"""
        return ImageGenerationResult(
            success=False,
            error_message=error_message
        )

    def supports_model(self, model_name: str) -> bool:
        """检查是否支持通义千问模型"""
        model_name_lower = model_name.lower()
        return (model_name_lower in [model.lower() for model in self.SUPPORTED_MODELS] or
                model_name_lower.startswith(('qwen-', 'tongyi-')))

    def get_supported_models(self) -> List[str]:
        """获取支持的通义千问模型列表"""
        return self.SUPPORTED_MODELS.copy()

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸列表"""
        return list(self.SIZE_MAPPING.keys())

    def get_supported_qualities(self) -> List[str]:
        """获取支持的图片质量列表"""
        return ["standard"]  # 通义千问主要支持标准质量

    def validate_config(self) -> bool:
        """验证配置是否完整"""
        required_fields = ['api_key', 'name']
        for field in required_fields:
            if not hasattr(self.model_config, field) or not getattr(self.model_config, field):
                return False
        return True

    def __del__(self):
        """析构函数，确保客户端关闭"""
        if self._client:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    asyncio.run(self.close())
            except:
                pass