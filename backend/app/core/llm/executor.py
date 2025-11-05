"""
AI执行器
负责AI模型调用的实际执行
"""

from typing import AsyncGenerator
from app.core.log_utils import get_logger
from app.core.llm.setting import ModelSetting
from app.core.llm.tracker import MLflowTracker

logger = get_logger(__name__)


class AIExecutor:
    """AI执行器"""

    def __init__(self, mlflow_tracker: MLflowTracker):
        """
        初始化AI执行器

        Args:
            mlflow_tracker: MLflow追踪器
        """
        self.mlflow_tracker = mlflow_tracker

    async def execute_stream(
        self,
        model: ModelSetting,
        actual_model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """
        执行流式AI调用

        Args:
            model: 模型配置
            actual_model_name: 实际模型名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            AsyncGenerator[str, None]: 内容块生成器
        """
        try:
            logger.info(
                "开始流式调用AI模型",
                operation="ai_stream_call_start",
                model_name=actual_model_name,
                provider=model.provider,
                mlflow_enabled=self.mlflow_tracker.is_initialized
            )

            client = model.get_client()
            stream_options = {"include_usage": True}

            stream = await self.mlflow_tracker.execute_with_tracking(
                model,
                lambda: client.chat.completions.create(
                    model=actual_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    stream_options=stream_options
                )
            )

            content_buffer = []

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    content_buffer.append(content)
                    yield content

            full_content = ''.join(content_buffer)
            logger.info(
                "流式AI调用完成",
                operation="ai_stream_call_completed",
                model_name=actual_model_name,
                response_length=len(full_content)
            )

        except Exception as e:
            logger.error(
                "流式AI调用失败",
                operation="ai_stream_call_failed",
                exception=e,
                model_name=actual_model_name
            )
            raise

    async def execute_sync(
        self,
        model: ModelSetting,
        actual_model_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        执行同步AI调用

        Args:
            model: 模型配置
            actual_model_name: 实际模型名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            str: AI响应内容
        """
        try:
            logger.info(
                "开始AI模型调用",
                operation="ai_call_start",
                model_name=actual_model_name,
                provider=model.provider,
                mlflow_enabled=self.mlflow_tracker.is_initialized
            )

            client = model.get_client()

            response = await self.mlflow_tracker.execute_with_tracking(
                model,
                lambda: client.chat.completions.create(
                    model=actual_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )

            content = response.choices[0].message.content

            logger.info(
                "AI模型调用完成",
                operation="ai_call_completed",
                model_name=actual_model_name,
                response_length=len(content)
            )

            return content

        except Exception as e:
            logger.error(
                "AI模型调用失败",
                operation="ai_call_failed",
                exception=e,
                model_name=actual_model_name
            )
            raise