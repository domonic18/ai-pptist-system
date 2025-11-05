"""
AI模型解析器
负责根据请求参数解析和选择合适的模型
"""

from typing import Optional, Tuple
from app.core.log_utils import get_logger
from app.core.llm.setting import ModelSetting
from app.core.llm.models import ModelManager

logger = get_logger(__name__)


class ModelResolver:
    """AI模型解析器"""

    def __init__(self, model_manager: ModelManager):
        """
        初始化模型解析器

        Args:
            model_manager: 模型管理器
        """
        self.model_manager = model_manager

    async def resolve_config(
        self,
        ai_model_config: Optional[dict],
        model_type: str = "text"
    ) -> Tuple[Optional[ModelSetting], Optional[str]]:
        """
        解析模型配置

        Args:
            ai_model_config: AI模型配置
            model_type: 模型类型，"text"或"image"

        Returns:
            Tuple[Optional[ModelSetting], Optional[str]]: 模型配置和实际模型名称
        """
        await self.model_manager.ensure_loaded()

        model_name = ai_model_config.get("model") if ai_model_config else None

        logger.debug(
            "解析模型配置",
            operation="resolve_model_config",
            ai_model_config=ai_model_config,
            model_name=model_name,
            model_type=model_type
        )

        if model_name:
            model = self._find_by_ai_name(model_name, model_type)
            if model:
                actual_model_name = model.ai_model_name
                logger.info(
                    "找到指定的模型配置",
                    operation="model_config_found",
                    requested_model=model_name,
                    actual_model_name=actual_model_name,
                    model_type=model_type
                )
                return model, actual_model_name

            # 使用默认模型
            default_model = (self.model_manager.get_default_text_model()
                           if model_type == "text"
                           else self.model_manager.get_default_image_model())
            logger.warning(
                "未找到指定的模型配置，使用默认模型",
                operation="model_not_found_use_default",
                requested_model=model_name,
                default_model=default_model.ai_model_name if default_model else None,
                model_type=model_type
            )
            return default_model, default_model.ai_model_name if default_model else None

        # 使用默认模型
        default_model = (self.model_manager.get_default_text_model()
                       if model_type == "text"
                       else self.model_manager.get_default_image_model())
        actual_model_name = default_model.ai_model_name if default_model else None
        logger.debug(
            "使用默认模型配置",
            operation="use_default_model",
            default_model=actual_model_name,
            model_type=model_type
        )
        return default_model, actual_model_name

    def _find_by_ai_name(self, ai_model_name: str, model_type: str = "text") -> Optional[ModelSetting]:
        """
        根据AI模型名称查找模型配置

        Args:
            ai_model_name: AI模型名称（传递给LLM的实际名称）
            model_type: 模型类型，"text"或"image"，默认为"text"

        Returns:
            Optional[ModelSetting]: 找到的模型配置，如果未找到则返回None
        """
        models_to_search = (self.model_manager.get_text_models()
                           if model_type == "text"
                           else self.model_manager.get_image_models())

        for model in models_to_search:
            if model.ai_model_name == ai_model_name:
                return model

        return None

    async def get_text_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取文本模型"""
        return self._find_by_ai_name(model_name, "text")

    async def get_image_model_by_name(self, model_name: str) -> Optional[ModelSetting]:
        """根据名称获取图像模型"""
        return self._find_by_ai_name(model_name, "image")