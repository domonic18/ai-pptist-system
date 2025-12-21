"""
统一的MLflow追踪Mixin
为所有AI Provider提供MLflow追踪功能
"""

from typing import Optional, Dict, Any, Callable
import time
import mlflow

from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker, ensure_mlflow_initialized

logger = get_logger(__name__)


class MLflowTracingMixin:
    """MLflow追踪Mixin类

    为继承它的类提供MLflow追踪功能
    需要子类实现：
    - model_config 属性
    """

    def __init__(self):
        """初始化MLflow追踪"""
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
                    operation="ai_provider_mlflow_init_success",
                    provider=self.__class__.__name__
                )
            else:
                logger.warning(
                    "MLflow追踪未启用，将在没有追踪的情况下运行",
                    operation="ai_provider_mlflow_init_disabled",
                    provider=self.__class__.__name__
                )
        except Exception as e:
            logger.error(
                "初始化MLflow追踪时出现错误",
                operation="ai_provider_mlflow_init_error",
                provider=self.__class__.__name__,
                exception=e
            )

    def _get_model_name(self) -> str:
        """获取模型名称"""
        if hasattr(self, 'model_config') and hasattr(self.model_config, 'model_name'):
            return self.model_config.model_name
        return "unknown"

    async def _with_mlflow_run(self, operation_name: str, call_func: Callable):
        """在MLflow run上下文中执行调用

        Args:
            operation_name: 操作名称
            call_func: 调用函数

        Returns:
            调用结果
        """
        if self.mlflow_tracker.is_initialized:
            model_name = self._get_model_name()
            run_name = f"{self.__class__.__name__}_{model_name}_{operation_name}"

            with self.mlflow_tracker.start_run(run_name=run_name):
                return await call_func()
        else:
            return await call_func()

    async def _with_mlflow_trace(
        self,
        operation_name: str,
        inputs: Dict[str, Any],
        call_func: Callable,
        **kwargs
    ) -> Any:
        """使用MLflow trace API进行追踪

        Args:
            operation_name: 操作名称
            inputs: 输入参数
            call_func: 实际执行函数
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        if not self.mlflow_tracker.is_initialized:
            return await call_func()

        model_name = self._get_model_name()
        trace_name = f"{self.__class__.__name__}_{model_name}_{operation_name}"

        start_time = time.time()

        try:
            # MLflow 2.8+ 支持 start_span API
            # 使用 mlflow.start_span 进行追踪
            with mlflow.start_span(
                name=trace_name,
                span_type="CHAIN"
            ) as span:
                # 记录输入
                span.set_inputs(inputs)

                # 执行实际调用
                result = await call_func()

                # 记录输出
                if hasattr(result, '__dict__'):
                    span.set_outputs(result.__dict__)
                else:
                    span.set_outputs({"result": str(result)})

                # 记录成功状态
                span.set_attribute("success", True)

                return result

        except Exception as e:
            # 记录错误
            try:
                with mlflow.start_span(
                    name=f"{trace_name}_error",
                    span_type="CHAIN"
                ) as error_span:
                    error_span.set_attribute("success", False)
                    error_span.set_attribute("error_message", str(e))
                    error_span.set_attribute("error_type", type(e).__name__)
            except:
                pass
            raise
        finally:
            duration = time.time() - start_time
            logger.info(
                f"{operation_name}完成",
                operation=f"ai_provider_{operation_name}",
                provider=self.__class__.__name__,
                model=model_name,
                duration_seconds=duration
            )

