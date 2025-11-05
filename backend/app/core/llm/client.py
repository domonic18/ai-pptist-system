"""
AI客户端，封装模型配置管理和MLflow追踪
重构后的门面类，协调各个组件
"""

from typing import Dict, Any, Optional, AsyncGenerator
from app.core.log_utils import get_logger
from app.core.llm.setting import ModelSetting
from app.core.llm.models import ModelManager
from app.core.llm.resolver import ModelResolver
from app.core.llm.tracker import MLflowTracker
from app.core.llm.executor import AIExecutor

logger = get_logger(__name__)


class AIClient:
    """AI客户端门面，协调各个组件"""

    def __init__(self):
        """初始化AI客户端"""
        # 初始化各个组件
        self.model_manager = ModelManager()
        self.model_resolver = ModelResolver(self.model_manager)
        self.mlflow_tracker = MLflowTracker()
        self.executor = AIExecutor(self.mlflow_tracker)

    async def get_text_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取文本模型"""
        return await self.model_resolver.get_text_model_by_name(model_name)

    async def get_image_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取图像模型"""
        return await self.model_resolver.get_image_model_by_name(model_name)

    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        defaults = {
            "text_model": self.model_manager.get_default_text_model().name if self.model_manager.get_default_text_model() else None,
            "image_model": self.model_manager.get_default_image_model().name if self.model_manager.get_default_image_model() else None,
        }

        return {
            "text_models": [
                {
                    "name": model.name,
                    "provider": model.provider,
                    "enabled": model.enabled,
                    "is_default": model.is_default,
                }
                for model in self.model_manager.get_text_models()
            ],
            "image_models": [
                {
                    "name": model.name,
                    "provider": model.provider,
                    "enabled": model.enabled,
                    "is_default": model.is_default,
                }
                for model in self.model_manager.get_image_models()
            ],
            "defaults": defaults,
        }

    async def stream_ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        ai_model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式调用AI模型API，支持MLflow追踪

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            ai_model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: 内容块生成器
        """
        try:
            # 解析模型配置
            model, actual_model_name = await self.model_resolver.resolve_config(
                ai_model_config, model_type="text"
            )

            if not model:
                raise ValueError("没有可用的AI模型配置")

            # 调试日志：记录最终选择的模型
            logger.debug(
                "流式调用模型选择调试",
                operation="stream_model_selection_debug",
                selected_model_name=actual_model_name,
                default_model_name=self.model_manager.get_default_text_model().ai_model_name if self.model_manager.get_default_text_model() else None
            )

            # 执行流式AI调用
            async for chunk in self.executor.execute_stream(
                model=model,
                actual_model_name=actual_model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield chunk

        except Exception as e:
            logger.error(
                "流式AI调用失败",
                operation="ai_stream_call_failed",
                exception=e,
                ai_model_config=ai_model_config
            )
            raise

    async def ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        ai_model_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        同步调用AI模型API，支持MLflow追踪

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            ai_model_config: 模型配置

        Returns:
            str: AI响应内容
        """
        try:
            # 解析模型配置
            model, actual_model_name = await self.model_resolver.resolve_config(
                ai_model_config, model_type="text"
            )

            if not model:
                raise ValueError("没有可用的AI模型配置")

            # 调试日志：记录最终选择的模型
            logger.debug(
                "模型选择调试",
                operation="model_selection_debug",
                selected_model_name=actual_model_name,
                default_model_name=self.model_manager.get_default_text_model().ai_model_name if self.model_manager.get_default_text_model() else None
            )

            # 执行同步AI调用
            return await self.executor.execute_sync(
                model=model,
                actual_model_name=actual_model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

        except Exception as e:
            logger.error(
                "AI模型调用失败",
                operation="ai_call_failed",
                exception=e,
                ai_model_config=ai_model_config
            )
            raise