"""
MLflow追踪器模块
基于MLflow官方最佳实践，提供AI模型调用的自动追踪功能
"""

import os
import mlflow
from typing import Optional, Dict, Any
from contextlib import contextmanager

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class MLflowTracker:
    """MLflow追踪器 - 基于官方最佳实践"""

    def __init__(self):
        self.is_initialized = False
        self.autolog_enabled = False

    def initialize(self) -> bool:
        """初始化MLflow追踪器"""
        if self.is_initialized:
            return True

        # 检查是否启用MLflow
        if not settings.enable_mlflow:
            logger.info("MLflow追踪已被禁用")
            return False

        try:
            # 设置MLflow跟踪URI
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

            # 设置实验
            try:
                experiment = mlflow.get_experiment_by_name(settings.mlflow_experiment_name)
                if experiment is None:
                    mlflow.create_experiment(settings.mlflow_experiment_name)
                mlflow.set_experiment(settings.mlflow_experiment_name)
                logger.info(f"MLflow实验已设置: {settings.mlflow_experiment_name}")
            except Exception as e:
                logger.warning(f"MLflow实验设置失败: {e}")

            self.is_initialized = True
            logger.info(f"MLflow追踪器初始化成功: {settings.mlflow_tracking_uri}")
            return True

        except Exception as e:
            logger.error(f"MLflow追踪器初始化失败: {e}")
            return False


    def enable_openai_autolog(self) -> bool:
        """启用OpenAI自动追踪"""
        if not self.is_initialized:
            if not self.initialize():
                logger.warning("MLflow未初始化，无法启用OpenAI自动追踪")
                return False

        try:
            # 启用OpenAI自动追踪，配置trace日志
            mlflow.openai.autolog(
                log_traces=True  # 启用trace日志
            )
            self.autolog_enabled = True
            logger.info("OpenAI自动追踪已启用 - 将自动捕获request/response内容")
            return True

        except Exception as e:
            logger.error(f"启用OpenAI自动追踪失败: {e}")
            return False

    @contextmanager
    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, Any]] = None):
        """启动MLflow运行的上下文管理器"""
        if not self.is_initialized:
            if not self.initialize():
                yield None
                return

        run = None
        try:
            run = mlflow.start_run(run_name=run_name, tags=tags)
            yield run
        except Exception as e:
            logger.error(f"启动MLflow运行失败: {e}")
            # 在异常情况下仍然yield None，让调用方处理
            yield None
        finally:
            if run is not None:
                try:
                    mlflow.end_run()
                except Exception as e:
                    logger.warning(f"结束MLflow运行时出错: {e}")





# 全局MLflow追踪器实例
mlflow_tracker = MLflowTracker()


def get_mlflow_tracker() -> MLflowTracker:
    """获取MLflow追踪器实例"""
    return mlflow_tracker


def ensure_mlflow_initialized() -> bool:
    """确保MLflow已初始化并启用自动追踪"""
    tracker = get_mlflow_tracker()
    if not tracker.is_initialized:
        tracker.initialize()
    if tracker.is_initialized and not tracker.autolog_enabled:
        tracker.enable_openai_autolog()
    return tracker.is_initialized and tracker.autolog_enabled

