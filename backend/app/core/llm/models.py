"""
AI模型管理器
负责模型配置的加载、缓存和管理
"""

from typing import List, Optional
from app.core.log_utils import get_logger
from app.core.llm.setting import ModelSetting
from app.db.database import AsyncSessionLocal
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)


class ModelManager:
    """AI模型管理器"""

    def __init__(self):
        """初始化模型管理器"""
        self.text_models: List[ModelSetting] = []
        self.image_models: List[ModelSetting] = []
        self.default_text_model: Optional[ModelSetting] = None
        self.default_image_model: Optional[ModelSetting] = None
        self._models_loaded = False

    async def ensure_loaded(self):
        """确保模型配置已加载（异步方式）"""
        if self._models_loaded:
            return
        await self._load_configs()
        self._models_loaded = True

    async def _load_configs(self):
        """从数据库加载模型配置（异步方式）"""
        self.text_models = []
        self.image_models = []

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
                cfg = self._db_to_setting(model)

                # 根据模型能力分类
                if model.supports_chat:
                    text_models.append(cfg)
                    if model.is_default and model.is_enabled and not default_text_model:
                        default_text_model = cfg

                if model.supports_image_generation:
                    image_models.append(cfg)
                    if model.is_default and model.is_enabled and not default_image_model:
                        default_image_model = cfg

            self.text_models = text_models
            self.image_models = image_models

            # 设置默认模型
            self.default_text_model = default_text_model or next((m for m in text_models if m.enabled), None)
            self.default_image_model = default_image_model or next((m for m in image_models if m.enabled), None)

            logger.info(
                "AI模型配置加载完成",
                operation="ai_models_config_loaded",
                text_models_count=len(self.text_models),
                image_models_count=len(self.image_models),
                default_text_model=self.default_text_model.name if self.default_text_model else None,
                default_image_model=self.default_image_model.name if self.default_image_model else None
            )

        except Exception as e:
            logger.error(
                "从数据库加载模型配置失败",
                operation="ai_models_db_load_failed",
                exception=e
            )
            raise

    @staticmethod
    def _db_to_setting(db_model) -> ModelSetting:
        """数据库模型到配置对象的转换"""
        cfg_dict = {
            "id": db_model.id,
            "name": db_model.name,
            "ai_model_name": db_model.ai_model_name,
            "api_key": db_model.api_key or "",
            "base_url": db_model.base_url,
            "enabled": db_model.is_enabled,
            "provider": db_model.provider,
            "description": "",
            "temperature": 0.7,
            "max_tokens": 1000,
            "is_default": db_model.is_default,
            "supports_vision": db_model.supports_vision
        }

        return ModelSetting(cfg_dict)

    def get_text_models(self) -> List[ModelSetting]:
        """获取所有文本模型"""
        return self.text_models.copy()

    def get_image_models(self) -> List[ModelSetting]:
        """获取所有图像模型"""
        return self.image_models.copy()

    def get_default_text_model(self) -> Optional[ModelSetting]:
        """获取默认文本模型"""
        return self.default_text_model

    def get_default_image_model(self) -> Optional[ModelSetting]:
        """获取默认图像模型"""
        return self.default_image_model