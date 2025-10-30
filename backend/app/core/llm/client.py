"""
AI客户端，封装模型配置管理和MLflow追踪
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from app.core.log_utils import get_logger
from app.core.mlflow_tracker import get_mlflow_tracker, ensure_mlflow_initialized
from app.core.llm.setting import ModelSetting
from app.db.database import AsyncSessionLocal
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)


class AIClient:
    """AI客户端，封装模型配置管理和MLflow追踪"""

    def __init__(self):
        # 初始化属性
        self.text_models: List[ModelSetting] = []
        self.image_models: List[ModelSetting] = []
        self.default_text_model: Optional[ModelSetting] = None
        self.default_image_model: Optional[ModelSetting] = None
        self._models_loaded = False

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
                    operation="ai_client_mlflow_init_success"
                )
            else:
                logger.warning(
                    "MLflow追踪未启用，将在没有追踪的情况下运行",
                    operation="ai_client_mlflow_init_disabled"
                )
        except Exception as e:
            logger.error(
                "初始化MLflow追踪时出现错误",
                operation="ai_client_mlflow_init_error",
                exception=e
            )

    async def _ensure_models_loaded(self):
        """确保模型配置已加载（异步方式）"""
        if self._models_loaded:
            return

        await self._load_model_configs()
        self._models_loaded = True

    async def _with_mlflow_run(self, model, call_func):
        """
        在MLflow run上下文中执行AI调用

        Args:
            model: AI模型
            call_func: AI调用函数

        Returns:
            AI调用结果
        """
        if self.mlflow_tracker.is_initialized:
            run_name = f"AI_Call_{model.name}"
            try:
                with self.mlflow_tracker.start_run(run_name=run_name):
                    return await call_func()
            except Exception as e:
                # 如果MLflow上下文管理器出现异常，直接调用函数而不使用MLflow
                logger.warning(
                    "MLflow上下文管理器异常，降级到无追踪模式",
                    operation="mlflow_context_fallback",
                    error=str(e)
                )
                return await call_func()
        else:
            return await call_func()

    async def _load_model_configs(self):
        """从数据库加载模型配置（异步方式）"""
        self.text_models = []
        self.image_models = []

        # 从数据库读取配置
        try:
            async with AsyncSessionLocal() as session:
                repo = AIModelRepository(session)
                db_models = await repo.list_models(enabled_only=False)

            if not db_models:
                logger.warning("没有找到任何AI模型配置")
                return

            text_models: List[ModelSetting] = []
            image_models: List[ModelSetting] = []
            default_text_model: Optional[ModelSetting] = None
            default_image_model: Optional[ModelSetting] = None

            for model in db_models:
                # API密钥
                api_key = model.api_key or ""

                # 创建模型配置
                cfg_dict = {
                    "name": model.name,
                    "api_key": api_key,
                    "base_url": model.base_url,
                    "enabled": model.is_enabled,
                    "provider": model.provider,
                    "description": "",
                    "temperature": float(model.max_tokens or 0.7) if hasattr(model, 'max_tokens') else 0.7,
                    "max_tokens": int(model.max_tokens or 1000) if hasattr(model, 'max_tokens') else 1000,
                    "is_default": model.is_default
                }

                cfg = ModelSetting(cfg_dict)

                # 根据模型类型分类
                # 这里需要根据实际业务逻辑判断模型类型
                # 暂时将所有模型都视为文本模型
                text_models.append(cfg)
                if model.is_default and model.is_enabled:
                    default_text_model = cfg

            self.text_models = text_models
            self.image_models = image_models

            # 设置默认模型
            self.default_text_model = default_text_model or next((m for m in text_models if m.enabled), None)
            self.default_image_model = default_image_model or next((m for m in image_models if m.enabled), None)

            logger.info(
                "AI模型配置加载完成",
                operation="ai_models_config_loaded",
                text_models_count=len(self.text_models),
                default_text_model=self.default_text_model.name if self.default_text_model else None
            )

        except Exception as e:
            logger.error(
                "从数据库加载模型配置失败",
                operation="ai_models_db_load_failed",
                exception=e
            )
            # 不再创建回退模型，直接抛出异常
            raise


    async def get_text_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取文本模型"""
        await self._ensure_models_loaded()
        return self._find_model_config(model_name, "text")

    async def get_image_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取图像模型"""
        await self._ensure_models_loaded()
        return self._find_model_config(model_name, "image")

    def _find_model_config(self, model_name: str, model_type: str) -> Optional[ModelSetting]:
        """查找指定模型配置"""
        models = self.text_models if model_type == "text" else self.image_models
        for model in models:
            if model.name == model_name:
                return model
        return None

    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        defaults = {
            "text_model": self.default_text_model.name if self.default_text_model else None,
            "image_model": self.default_image_model.name if self.default_image_model else None,
        }

        return {
            "text_models": [
                {
                    "name": model.name,
                    "provider": model.provider,
                    "enabled": model.enabled,
                    "is_default": model.is_default,
                }
                for model in self.text_models
            ],
            "image_models": [
                {
                    "name": model.name,
                    "provider": model.provider,
                    "enabled": model.enabled,
                    "is_default": model.is_default,
                }
                for model in self.image_models
            ],
            "defaults": defaults,
        }

    async def stream_ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式调用AI模型API，支持MLflow追踪

        使用OpenAI官方客户端的流式接口，自动记录MLflow追踪

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: 内容块生成器
        """
        try:
            # 确保模型配置已加载
            await self._ensure_models_loaded()

            # 获取模型配置
            model_name = model_config.get("model") if model_config else None
            model = await self.get_text_model_by_name(model_name) if model_name else self.default_text_model

            if not model:
                raise ValueError("没有可用的AI模型配置")

            logger.info(
                "开始流式调用AI模型",
                operation="ai_stream_call_start",
                model_name=model.name,
                provider=model.provider,
                mlflow_enabled=self.mlflow_tracker.is_initialized
            )

            # 使用OpenAI官方客户端进行流式调用
            # MLflow会自动追踪OpenAI调用（包括request/response内容）
            client = model.get_client()

            # 启用流式调用的token使用统计
            stream_options = {"include_usage": True}

            # 在MLflow run上下文中执行AI调用，确保traces关联到run
            stream = await self._with_mlflow_run(model, lambda: client.chat.completions.create(
                model=model.name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options=stream_options
            ))

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
                model_name=model.name,
                response_length=len(full_content)
            )

        except Exception as e:
            logger.error(
                "流式AI调用失败",
                operation="ai_stream_call_failed",
                exception=e,
                model_config=model_config
            )
            raise

    async def ai_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        同步调用AI模型API，支持MLflow追踪

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            str: AI响应内容
        """
        try:
            # 确保模型配置已加载
            await self._ensure_models_loaded()

            # 获取模型配置
            model_name = model_config.get("model") if model_config else None
            model = await self.get_text_model_by_name(model_name) if model_name else self.default_text_model

            if not model:
                raise ValueError("没有可用的AI模型配置")

            logger.info(
                "开始AI模型调用",
                operation="ai_call_start",
                model_name=model.name,
                provider=model.provider,
                mlflow_enabled=self.mlflow_tracker.is_initialized
            )

            # 使用OpenAI官方客户端进行调用
            # MLflow会自动追踪OpenAI调用（包括request/response内容）
            client = model.get_client()

            # 在MLflow run上下文中执行AI调用，确保traces关联到run
            response = await self._with_mlflow_run(model, lambda: client.chat.completions.create(
                model=model.name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            ))

            content = response.choices[0].message.content

            logger.info(
                "AI模型调用完成",
                operation="ai_call_completed",
                model_name=model.name,
                response_length=len(content)
            )

            return content

        except Exception as e:
            logger.error(
                "AI模型调用失败",
                operation="ai_call_failed",
                exception=e,
                model_config=model_config
            )
            raise