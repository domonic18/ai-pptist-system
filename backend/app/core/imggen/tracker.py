"""
MLflow追踪Mixin
为图片生成提供商提供MLflow追踪功能
"""

from typing import Optional, Dict, Any, Callable
import time

from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker, ensure_mlflow_initialized
from .models import ImageGenerationResult

logger = get_logger(__name__)


class MLflowTracingMixin:
    """MLflow追踪Mixin类
    
    为继承它的类提供MLflow追踪功能
    需要子类实现：
    - model_config 属性
    - _generate_image_internal() 方法
    """
    
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
    
    async def _with_mlflow_run(self, operation_name: str, call_func: Callable):
        """在MLflow run上下文中执行图片生成调用
        
        Args:
            operation_name: 操作名称
            call_func: 图片生成调用函数
            
        Returns:
            图片生成结果
        """
        if self.mlflow_tracker.is_initialized:
            # 获取模型名称
            model_name = self._get_model_name()
            
            run_name = f"ImageGeneration_{self.__class__.__name__}_{model_name}_{operation_name}"
            with self.mlflow_tracker.start_run(run_name=run_name):
                return await call_func()
        else:
            return await call_func()
    
    async def _with_mlflow_trace(
        self,
        operation_name: str,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """使用MLflow 3.1.4的trace API进行图片生成追踪
        
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
        inputs = self._prepare_trace_inputs(prompt, size, quality, **kwargs)
        
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
            result = await self._with_mlflow_run(
                operation_name,
                lambda: self._execute_with_tracing(
                    operation_name, prompt, size, quality, inputs, start_time, **kwargs
                )
            )
            
            # 记录完成日志
            self._log_generation_result(result, start_time)
            
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
    
    async def _execute_with_tracing(
        self,
        operation_name: str,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """在MLflow trace上下文中执行实际的图片生成
        
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
            execution_time = time.time() - start_time if start_time is not None else 0
            
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
                self._set_span_attributes(inputs, outputs, result, prompt, execution_time)
            
            return result
        
        # 执行带追踪的图片生成
        return await traced_generation()
    
    def _get_model_name(self) -> str:
        """获取模型名称
        
        Returns:
            str: 模型名称
        """
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
        return model_name
    
    def _prepare_trace_inputs(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """准备追踪输入数据
        
        Args:
            prompt: 图片描述提示词
            size: 图片尺寸
            quality: 图片质量
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 输入数据字典
        """
        model_name = self._get_model_name()
        
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
        
        return inputs
    
    def _set_span_attributes(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        result: ImageGenerationResult,
        prompt: str,
        execution_time: float
    ):
        """设置MLflow span属性
        
        Args:
            inputs: 输入数据
            outputs: 输出数据
            result: 生成结果
            prompt: 提示词
            execution_time: 执行时间
        """
        try:
            import mlflow
            
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
    
    def _log_generation_result(self, result: ImageGenerationResult, start_time: float):
        """记录生成结果日志
        
        Args:
            result: 生成结果
            start_time: 开始时间
        """
        execution_time = time.time() - start_time
        
        if result.success:
            logger.info(
                "图片生成完成",
                operation="image_generation_completed",
                provider=self.__class__.__name__,
                execution_time_seconds=round(execution_time, 3),
                has_image_url=bool(result.image_url)
            )
        else:
            logger.error(
                "图片生成失败",
                operation="image_generation_failed",
                provider=self.__class__.__name__,
                error_message=result.error_message,
                execution_time_seconds=round(execution_time, 3)
            )

