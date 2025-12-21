"""
火山引擎方舟图片生成提供商
支持火山引擎方舟文生图API
"""

import time
import asyncio
from typing import Optional, List, Dict, Any
from app.core.log_utils import get_logger
from app.core.imggen.base import BaseImageProvider, ImageGenerationResult

logger = get_logger(__name__)


class VolcengineArkProvider(BaseImageProvider):
    """火山引擎方舟图片生成提供商"""

    # API配置常量
    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DEFAULT_TIMEOUT = 60
    DEFAULT_SIZE = "1024x1024"
    DEFAULT_QUALITY = "standard"

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "doubao-seedream-3-0-t2i-250415",
        "doubao-seedream-3-0-t2i",
        "doubao-seedream-2-0-t2i",
        "doubao-seedream-1-0-t2i",
        "doubao-image-generation",
        "seedream-image"
    ]

    def __init__(self, model_config):
        super().__init__(model_config)
        self._client = None
        self._api_key = getattr(model_config, 'api_key', '')
        self._base_url = getattr(model_config, 'base_url', self.DEFAULT_BASE_URL)

    async def _ensure_client(self):
        """确保客户端已初始化"""
        if self._client is None:
            await self._create_client()

    async def _create_client(self):
        """创建火山引擎方舟客户端"""
        try:
            # 这里需要导入volcenginesdkarkruntime SDK
            from volcenginesdkarkruntime import Ark

            if not self._api_key:
                raise ValueError("火山引擎方舟API密钥未配置")

            # 清理base_url：去除前后空格
            base_url = self._base_url.strip() if self._base_url else self.DEFAULT_BASE_URL

            # 确保base_url包含协议前缀
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
                logger.warning("base_url缺少协议前缀，已自动添加https://", extra={"base_url": base_url})

            # 创建客户端
            self._client = Ark(
                api_key=self._api_key,
                base_url=base_url,
                timeout=getattr(self.model_config, 'timeout', self.DEFAULT_TIMEOUT)
            )

            logger.info("火山引擎方舟客户端初始化成功", extra={
                "model": self.model_config.name,
                "base_url": base_url
            })

        except ImportError as e:
            error_msg = f"火山引擎方舟SDK未安装，请安装: pip install volcenginesdkarkruntime - {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"火山引擎方舟客户端初始化失败: {str(e)}"
            logger.error(error_msg, extra={"error": str(e)})
            raise ValueError(error_msg)

    async def close(self):
        """关闭客户端"""
        if self._client:
            # 火山引擎SDK可能不需要显式关闭
            self._client = None

    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """实际生成图片 - 火山引擎方舟实现（由MLflow追踪调用）"""
        try:
            await self._ensure_client()

            if not self._client:
                return self._create_error_result("火山引擎方舟客户端未初始化")

            # 准备API参数
            api_params = {
                'model': self.model_config.name,
                'prompt': prompt,
                'size': size or self.DEFAULT_SIZE
            }

            # 添加其他可选参数
            if 'style' in kwargs:
                api_params['style'] = kwargs['style']
            if 'negative_prompt' in kwargs:
                api_params['negative_prompt'] = kwargs['negative_prompt']
            if 'seed' in kwargs:
                api_params['seed'] = kwargs['seed']

            logger.info("调用火山引擎方舟图片生成", extra={
                "model": self.model_config.name,
                "prompt_length": len(prompt),
                "size": api_params['size'],
                "quality": quality
            })

            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._sync_generate_image,
                api_params
            )

            # 处理响应
            image_url = self._extract_image_url(response)

            if image_url:
                logger.info("火山引擎方舟图片生成成功", extra={
                    "image_url_preview": image_url[:50]
                })

                metadata = self._extract_metadata(response, api_params, quality)

                return ImageGenerationResult(
                    success=True,
                    image_url=image_url,
                    metadata=metadata
                )
            else:
                error_msg = self._analyze_response_for_errors(response)
                if not error_msg:
                    error_msg = "火山引擎方舟API返回空数据"

                logger.warning("火山引擎方舟图片生成失败", extra={
                    "error": error_msg,
                    "response_preview": str(response)[:200]
                })

                return self._create_error_result(error_msg)

        except Exception as e:
            error_msg = f"火山引擎方舟图片生成失败: {str(e)}"
            logger.error(error_msg, extra={"error": str(e)})
            return self._create_error_result(error_msg)

    def _sync_generate_image(self, api_params: Dict[str, Any]) -> Any:
        """同步调用火山引擎方舟API"""
        try:
            # 调用API
            response = self._client.images.generate(**api_params)
            return response

        except Exception as e:
            logger.error("同步调用火山引擎方舟API失败", extra={"error": str(e)})
            raise

    def _extract_image_url(self, response: Any) -> Optional[str]:
        """提取火山引擎方舟格式的图片URL"""
        try:
            if hasattr(response, 'data') and response.data and len(response.data) > 0:
                first_item = response.data[0]
                if hasattr(first_item, 'url'):
                    return first_item.url

            return None

        except Exception as e:
            logger.warning("提取火山引擎方舟图片URL失败", extra={"error": str(e)})
            return None

    def _extract_metadata(self, response: Any, api_params: Dict[str, Any], quality: Optional[str] = None) -> Dict[str, Any]:
        """提取火山引擎方舟格式的元数据"""
        metadata = {
            'provider': 'volcengine_ark',
            'model': api_params.get('model'),
            'size': api_params.get('size'),
            'quality': quality,
            'created': int(time.time())
        }

        # 添加火山引擎方舟特定的元数据
        if hasattr(response, 'created') and response.created:
            metadata['created'] = response.created
        if hasattr(response, 'model') and response.model:
            metadata['response_model'] = response.model
        if hasattr(response, 'usage') and response.usage:
            metadata['usage'] = response.usage

        return metadata

    def _analyze_response_for_errors(self, response: Any) -> str:
        """分析响应中的错误信息"""
        try:
            if not response:
                return "空响应"

            # 检查是否有错误信息
            if hasattr(response, 'error') and response.error:
                error_info = response.error
                if isinstance(error_info, dict):
                    return f"API错误: {error_info.get('message', '未知错误')}"
                else:
                    return f"API错误: {str(error_info)}"

            # 检查是否有拒绝生成的内容
            if hasattr(response, 'data') and not response.data:
                return "API返回空数据，可能由于内容政策限制或参数错误"

            return ""

        except Exception as e:
            logger.warning("分析火山引擎方舟响应错误时发生异常", extra={"error": str(e)})
            return "无法解析API响应内容"

    def _create_error_result(self, error_message: str) -> ImageGenerationResult:
        """创建错误结果"""
        return ImageGenerationResult(
            success=False,
            error_message=error_message
        )

    def supports_model(self, model_name: str) -> bool:
        """检查是否支持火山引擎方舟模型"""
        model_name_lower = model_name.lower()
        return (model_name_lower in [model.lower() for model in self.SUPPORTED_MODELS] or
                model_name_lower.startswith(('doubao-', 'seedream-')))

    def get_supported_models(self) -> List[str]:
        """获取支持的火山引擎方舟模型列表"""
        return self.SUPPORTED_MODELS.copy()

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸列表"""
        # 火山引擎方舟支持的常见尺寸
        return [
            "512x512",
            "768x768",
            "1024x1024",
            "1024x768",
            "768x1024",
            "1024x1792",
            "1792x1024"
        ]

    def get_supported_qualities(self) -> List[str]:
        """获取支持的图片质量列表"""
        return ["standard", "hd"]  # 假设支持多种质量

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