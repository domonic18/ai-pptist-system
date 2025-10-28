"""
图片生成提供商基类
定义所有图片生成提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time

from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker, ensure_mlflow_initialized

logger = get_logger(__name__)


@dataclass
class ImageGenerationResult:
    """图片生成结果"""
    success: bool
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseImageProvider(ABC):
    """图片生成提供商基类"""

    def __init__(self, model_config):
        self.model_config = model_config
        # 初始化MLflow追踪器
        self.mlflow_tracker = get_mlflow_tracker()
        self._initialize_mlflow()

    def _initialize_mlflow(self):
        """初始化MLflow追踪"""
        try:
            # 确保MLflow已初始化并启用自动追踪
            mlflow_enabled = ensure_mlflow_initialized()

            if mlflow_enabled:
                logger.info(
                    "MLflow追踪已启用",
                    operation="image_provider_mlflow_init_success",
                    provider=self.__class__.__name__
                )
            else:
                logger.warning(
                    "MLflow追踪未启用，将在没有追踪的情况下运行",
                    operation="image_provider_mlflow_init_disabled",
                    provider=self.__class__.__name__
                )
        except Exception as e:
            logger.error(
                "初始化MLflow追踪时出现错误",
                operation="image_provider_mlflow_init_error",
                provider=self.__class__.__name__,
                exception=e
            )

    async def _with_mlflow_run(self, operation_name: str, call_func):
        """
        在MLflow run上下文中执行图片生成调用

        Args:
            operation_name: 操作名称
            call_func: 图片生成调用函数

        Returns:
            图片生成结果
        """
        if self.mlflow_tracker.is_initialized:
            # 获取模型名称
            model_name = "unknown"
            if self.model_config:
                if hasattr(self.model_config, 'get'):
                    model_name = self.model_config.get("model", getattr(self.model_config, 'name', "unknown"))
                elif hasattr(self.model_config, 'name'):
                    model_name = self.model_config.name
                elif hasattr(self.model_config, 'model'):
                    model_name = self.model_config.model

            run_name = f"ImageGeneration_{self.__class__.__name__}_{model_name}_{operation_name}"
            with self.mlflow_tracker.start_run(run_name=run_name):
                return await call_func()
        else:
            return await call_func()

    async def _with_mlflow_trace(self, operation_name: str, prompt: str,
                                size: Optional[str] = None, quality: Optional[str] = None,
                                **kwargs):
        """
        使用MLflow 3.1.4的trace API进行图片生成追踪

        Args:
            operation_name: 操作名称
            prompt: 图片描述提示词
            size: 图片尺寸
            quality: 图片质量
            **kwargs: 其他参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        # 如果MLflow未初始化，直接调用内部方法
        if not self.mlflow_tracker.is_initialized:
            return await self._generate_image_internal(prompt, size, quality, **kwargs)

        start_time = time.time()

        # 准备追踪数据
        model_name = "unknown"
        if self.model_config:
            if hasattr(self.model_config, 'get'):
                # 如果model_config支持get方法（字典或类似对象）
                model_name = self.model_config.get("model", getattr(self.model_config, 'name', "unknown"))
            elif hasattr(self.model_config, 'name'):
                # 如果model_config有name属性
                model_name = self.model_config.name
            elif hasattr(self.model_config, 'model'):
                # 如果model_config有model属性
                model_name = self.model_config.model

        inputs = {
            "prompt": prompt,
            "provider": self.__class__.__name__,
            "model": model_name
        }

        if size:
            inputs["size"] = size
        if quality:
            inputs["quality"] = quality

        # 添加其他参数，过滤掉敏感信息
        for key, value in kwargs.items():
            if key.lower() not in ["api_key", "token", "secret", "password"]:
                inputs[key] = value

        logger.info(
            "开始图片生成",
            operation="image_generation_start",
            provider=self.__class__.__name__,
            prompt_length=len(prompt),
            size=size,
            mlflow_enabled=True
        )

        try:
            # 在MLflow run上下文中执行图片生成，确保traces关联到run
            result = await self._with_mlflow_run(operation_name, lambda: self._execute_with_tracing(
                operation_name, prompt, size, quality, inputs, start_time, **kwargs
            ))

            # 记录完成日志
            if result.success:
                logger.info(
                    "图片生成完成",
                    operation="image_generation_completed",
                    provider=self.__class__.__name__,
                    execution_time_seconds=round(time.time() - start_time, 3),
                    has_image_url=bool(result.image_url)
                )
            else:
                logger.error(
                    "图片生成失败",
                    operation="image_generation_failed",
                    provider=self.__class__.__name__,
                    error_message=result.error_message,
                    execution_time_seconds=round(time.time() - start_time, 3)
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                "图片生成过程中发生异常",
                operation="image_generation_exception",
                provider=self.__class__.__name__,
                exception=e,
                execution_time_seconds=round(execution_time, 3)
            )

            # 返回错误结果
            return ImageGenerationResult(
                success=False,
                error_message=str(e),
                metadata={"execution_time_seconds": round(execution_time, 3)}
            )

    async def _execute_with_tracing(self, operation_name: str, prompt: str,
                                  size: Optional[str] = None, quality: Optional[str] = None,
                                  inputs: Optional[Dict[str, Any]] = None, start_time: Optional[float] = None,
                                  **kwargs) -> 'ImageGenerationResult':
        """
        在MLflow trace上下文中执行实际的图片生成

        Args:
            operation_name: 操作名称
            prompt: 图片描述提示词
            size: 图片尺寸
            quality: 图片质量
            inputs: 输入数据（已准备好的）
            start_time: 开始时间
            **kwargs: 其他参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        # 使用MLflow 3.1.4的trace API
        import mlflow
        from mlflow.entities import SpanType

        # 创建一个trace装饰的函数来执行图片生成
        @mlflow.trace(span_type=SpanType.LLM)
        async def traced_generation():
            # 执行实际的图片生成
            result = await self._generate_image_internal(prompt, size, quality, **kwargs)

            # 计算执行时间
            if start_time is not None:
                execution_time = time.time() - start_time
            else:
                execution_time = 0

            # 准备输出数据
            outputs = {
                "success": result.success,
                "image_url": result.image_url,
                "error_message": result.error_message,
                "metadata": result.metadata or {},
                "execution_time_seconds": round(execution_time, 3),
                "provider": self.__class__.__name__
            }

            # 记录参数和输出到当前的span
            if inputs is not None:
                try:
                    # 获取当前活动的span
                    current_span = mlflow.get_current_active_span()
                    if current_span:
                        # 设置span的输入和输出
                        current_span.set_inputs(inputs)
                        current_span.set_outputs(outputs)

                        # 设置属性
                        current_span.set_attribute("provider", self.__class__.__name__)
                        current_span.set_attribute("prompt_length", len(prompt))
                        current_span.set_attribute("execution_time_seconds", round(execution_time, 3))
                        current_span.set_attribute("success", result.success)

                        if result.image_url:
                            current_span.set_attribute("has_image_url", True)
                            current_span.set_attribute("image_url", result.image_url)

                        if result.error_message:
                            current_span.set_attribute("error_message", result.error_message)

                except Exception as span_error:
                    logger.warning(
                        "设置MLflow span属性失败",
                        operation="mlflow_span_set_failed",
                        exception=span_error
                    )

            return result

        # 执行带追踪的图片生成
        return await traced_generation()

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
        pass

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """
        检查是否支持指定模型

        Args:
            model_name: 模型名称

        Returns:
            bool: 是否支持该模型
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        获取支持的模型列表

        Returns:
            List[str]: 支持的模型名称列表
        """
        pass

    @abstractmethod
    def get_supported_sizes(self) -> List[str]:
        """
        获取支持的图片尺寸列表

        Returns:
            List[str]: 支持的尺寸列表
        """
        pass

    @abstractmethod
    def get_supported_qualities(self) -> List[str]:
        """
        获取支持的图片质量列表

        Returns:
            List[str]: 支持的质量列表
        """
        pass