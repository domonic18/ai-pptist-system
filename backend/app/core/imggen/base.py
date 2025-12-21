"""
图片生成提供商基类
定义所有图片生成提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker
from .models import ImageGenerationResult
from .tracker import MLflowTracingMixin

logger = get_logger(__name__)


class BaseImageProvider(MLflowTracingMixin, ABC):
    """图片生成提供商基类"""

    def __init__(self, model_config):
        """初始化图片生成提供商
        
        Args:
            model_config: 模型配置对象
        """
        self.model_config = model_config
        # 初始化MLflow追踪器
        self.mlflow_tracker = get_mlflow_tracker()
        self._initialize_mlflow()

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片（带MLflow追踪）

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸，如 "1024x1024"
            quality: 图片质量，如 "standard" 或 "hd"
            **kwargs: 其他提供商特定参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        # 使用带追踪的方法
        return await self._with_mlflow_trace(
            operation_name="generate_image",
            prompt=prompt,
            size=size,
            quality=quality,
            **kwargs
        )

    @abstractmethod
    async def _generate_image_internal(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        实际的图片生成方法（由子类实现）

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸，如 "1024x1024"
            quality: 图片质量，如 "standard" 或 "hd"
            **kwargs: 其他提供商特定参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        ...

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """
        检查是否支持指定模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否支持该模型
        """
        ...

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        获取支持的模型列表

        Returns:
            List[str]: 支持的模型名称列表
        """
        ...

    @abstractmethod
    def get_supported_sizes(self) -> List[str]:
        """
        获取支持的图片尺寸列表

        Returns:
            List[str]: 支持的尺寸列表
        """
        ...

    @abstractmethod
    def get_supported_qualities(self) -> List[str]:
        """
        获取支持的图片质量列表

        Returns:
            List[str]: 支持的质量列表
        """
        ...