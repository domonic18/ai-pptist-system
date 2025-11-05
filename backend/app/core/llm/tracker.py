"""
MLflow追踪器
负责MLflow追踪的编排和管理
"""

from typing import Callable, Any
from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker, ensure_mlflow_initialized

logger = get_logger(__name__)


class MLflowTracker:
    """MLflow追踪器"""

    def __init__(self):
        """初始化MLflow追踪器"""
        self.mlflow_tracker = get_mlflow_tracker()
        self._initialize()

    def _initialize(self):
        """初始化MLflow追踪"""
        try:
            mlflow_enabled = ensure_mlflow_initialized()

            if mlflow_enabled:
                logger.info(
                    "MLflow追踪已启用",
                    operation="mlflow_tracker_init_success"
                )
            else:
                logger.warning(
                    "MLflow追踪未启用，将在没有追踪的情况下运行",
                    operation="mlflow_tracker_init_disabled"
                )
        except Exception as e:
            logger.error(
                "初始化MLflow追踪时出现错误",
                operation="mlflow_tracker_init_error",
                exception=e
            )

    async def execute_with_tracking(self, model, call_func: Callable[[], Any]) -> Any:
        """
        在MLflow run上下文中执行函数调用

        Args:
            model: AI模型
            call_func: 要执行的函数

        Returns:
            Any: 函数执行结果
        """
        if self.mlflow_tracker.is_initialized:
            run_name = f"AI_Call_{model.name}"
            try:
                with self.mlflow_tracker.start_run(run_name=run_name):
                    return await call_func()
            except Exception as e:
                logger.warning(
                    "MLflow上下文管理器异常，降级到无追踪模式",
                    operation="mlflow_context_fallback",
                    error=str(e)
                )
                return await call_func()
        else:
            return await call_func()

    @property
    def is_initialized(self) -> bool:
        """检查MLflow是否已初始化"""
        return self.mlflow_tracker.is_initialized