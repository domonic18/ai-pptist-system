"""
AI模型管理服务
处理AI模型的CRUD操作和业务逻辑
"""

import time
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)


class ManagementService:
    """AI模型管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIModelRepository(db)

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取指定模型"""
        try:
            model = await self.repository.get_model_by_id(model_id)
            return self._model_to_dict(model) if model else None
        except Exception as e:
            logger.error(
                "获取AI模型失败",
                extra={
                    "model_id": model_id,
                    "error": str(e)
                }
            )
            return None

    async def get_model_for_edit(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型详情用于编辑（包含敏感信息如API密钥）"""
        try:
            model = await self.repository.get_model_by_id(model_id)
            if not model:
                return None

            return {
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "ai_model_name": model.ai_model_name,
                "base_url": model.base_url,
                "api_key": model.api_key,
                "max_tokens": model.max_tokens,
                "is_enabled": model.is_enabled,
                "is_default": model.is_default,
                "model_settings": model.model_settings or {},
                "created_at": model.created_at,
                "updated_at": model.updated_at
            }
        except Exception as e:
            logger.error(
                "获取AI模型详情失败",
                extra={
                    "model_id": model_id,
                    "error": str(e)
                }
            )
            return None

    async def list_models(
        self,
        enabled_only: bool = True,
        supports_image_generation: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """获取模型列表"""
        try:
            models = await self.repository.list_models(
                enabled_only=enabled_only,
                supports_image_generation=supports_image_generation
            )
            return [self._model_to_dict(model) for model in models]
        except Exception as e:
            logger.error(
                "获取AI模型列表失败",
                extra={
                    "error": str(e),
                    "supports_image_generation": supports_image_generation
                }
            )
            return []

    async def get_default_model(self) -> Optional[Dict[str, Any]]:
        """获取默认模型"""
        try:
            model = await self.repository.get_default_model()
            return self._model_to_dict(model) if model else None
        except Exception as e:
            logger.error(
                "获取默认AI模型失败",
                extra={
                    "error": str(e)
                }
            )
            return None

    async def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新模型"""
        try:
            # 检查是否已存在同名模型
            existing_model = await self.repository.get_model_by_name(model_data["name"])
            if existing_model:
                raise ValueError(f"已存在同名模型: {model_data['name']}")

            # 创建新模型
            new_model = await self.repository.create_model(
                name=model_data["name"],
                provider=model_data["provider"],
                ai_model_name=model_data["ai_model_name"],
                base_url=model_data["base_url"],
                api_key=model_data.get("api_key", ""),
                max_tokens=model_data.get("max_tokens", "8192"),
                context_window=model_data.get("context_window", "16384"),
                model_settings=model_data.get("model_settings", {}),
                is_enabled=model_data.get("is_enabled", True),
                is_default=model_data.get("is_default", False),
                # 能力配置字段
                supports_chat=model_data.get("supports_chat", True),
                supports_embeddings=model_data.get("supports_embeddings", False),
                supports_vision=model_data.get("supports_vision", False),
                supports_tools=model_data.get("supports_tools", False),
                supports_image_generation=model_data.get("supports_image_generation", False)
            )

            logger.info(
                "成功创建AI模型",
                extra={
                    "model_id": new_model.id,
                    "model_name": new_model.name,
                    "provider": new_model.provider
                }
            )

            return self._model_to_dict(new_model)

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "创建AI模型失败",
                extra={
                    "error": str(e),
                    "model_name": model_data.get("name")
                }
            )
            raise

    async def update_model(self, model_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新模型"""
        try:
            # 构建更新字段
            update_fields = {}
            if "name" in update_data:
                update_fields["name"] = update_data["name"]
            if "provider" in update_data:
                update_fields["provider"] = update_data["provider"]
            if "ai_model_name" in update_data:
                update_fields["ai_model_name"] = update_data["ai_model_name"]
            if "base_url" in update_data:
                update_fields["base_url"] = update_data["base_url"]
            if "api_key" in update_data:
                update_fields["api_key"] = update_data["api_key"]
            if "max_tokens" in update_data:
                update_fields["max_tokens"] = update_data["max_tokens"]
            if "context_window" in update_data:
                update_fields["context_window"] = update_data["context_window"]
            if "model_settings" in update_data:
                update_fields["model_settings"] = update_data["model_settings"]
            if "is_enabled" in update_data:
                update_fields["is_enabled"] = update_data["is_enabled"]
            if "is_default" in update_data:
                update_fields["is_default"] = update_data["is_default"]
            # 能力配置字段
            if "supports_chat" in update_data:
                update_fields["supports_chat"] = update_data["supports_chat"]
            if "supports_embeddings" in update_data:
                update_fields["supports_embeddings"] = update_data["supports_embeddings"]
            if "supports_vision" in update_data:
                update_fields["supports_vision"] = update_data["supports_vision"]
            if "supports_tools" in update_data:
                update_fields["supports_tools"] = update_data["supports_tools"]
            if "supports_image_generation" in update_data:
                update_fields["supports_image_generation"] = update_data["supports_image_generation"]

            # 移除手动设置updated_at，数据库触发器会自动处理

            # 更新模型
            updated_model = await self.repository.update_model(model_id, **update_fields)

            if not updated_model:
                return None

            logger.info(
                "成功更新AI模型",
                extra={
                    "model_id": model_id,
                    "model_name": updated_model.name
                }
            )

            return self._model_to_dict(updated_model)

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "更新AI模型失败",
                extra={
                    "error": str(e),
                    "model_id": model_id
                }
            )
            raise

    async def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        try:
            # 先获取模型信息用于日志记录
            model = await self.repository.get_model_by_id(model_id)
            if not model:
                return False

            success = await self.repository.delete_model(model_id)

            if success:
                logger.info(
                    "成功删除AI模型",
                    extra={
                        "model_id": model_id,
                        "model_name": model.name
                    }
                )

            return success

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "删除AI模型失败",
                extra={
                    "error": str(e),
                    "model_id": model_id
                }
            )
            raise

    def _model_to_dict(self, model) -> Dict[str, Any]:
        """将模型对象转换为字典"""
        return {
            "id": model.id,
            "name": model.name,
            "provider": model.provider,
            "ai_model_name": model.ai_model_name,
            "base_url": model.base_url,
            "max_tokens": model.max_tokens,
            "context_window": model.context_window,
            "is_enabled": model.is_enabled,
            "is_default": model.is_default,
            "model_settings": model.model_settings or {},
            # 能力配置 - 直接使用数据库值，不提供默认值
            "supports_chat": model.supports_chat,
            "supports_embeddings": model.supports_embeddings,
            "supports_vision": model.supports_vision,
            "supports_tools": model.supports_tools,
            "supports_image_generation": model.supports_image_generation,
            "created_at": model.created_at,
            "updated_at": model.updated_at
        }

    async def get_supported_image_generation_models(self) -> List[Dict[str, Any]]:
        """
        获取支持图片生成的模型列表

        Returns:
            List[Dict[str, Any]]: 支持图片生成的模型列表
        """
        try:
            logger.info("获取支持图片生成的模型列表")

            models = await self.repository.list_models(supports_image_generation=True)

            result = []
            for model in models:
                result.append({
                    "name": model.name,
                    "ai_model_name": model.ai_model_name,
                    "provider": model.provider,
                    "is_enabled": model.is_enabled,
                    "is_default": model.is_default,
                    "base_url": model.base_url,
                    "max_tokens": model.max_tokens,
                    "context_window": model.context_window,
                    "model_settings": model.model_settings or {}
                })

            logger.info(f"成功获取 {len(result)} 个支持图片生成的模型")
            return result

        except Exception as e:
            logger.error(
                "获取支持图片生成的模型列表失败",
                extra={"error": str(e)}
            )
            return []

    async def get_model_config_for_image_generation(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取用于图片生成的模型配置"""
        try:
            # 优先通过name字段查找
            model = await self.repository.get_model_by_name(model_name)

            # 如果找不到，尝试通过model_name字段查找
            if not model:
                all_models = await self.repository.list_models(
                    supports_image_generation=True
                )
                model = next((m for m in all_models if m.ai_model_name == model_name), None)

            if not model:
                logger.error("模型不存在", extra={
                    "model_name": model_name,
                    "note": "请检查前端传递的model_name是否与数据库中的model_name字段匹配"
                })
                return None

            if not model.supports_image_generation:
                logger.error("模型不支持图片生成", extra={
                    "model_name": model_name,
                    "provider": model.provider
                })
                return None

            return {
                "id": model.id,
                "name": model.name,
                "ai_model_name": model.ai_model_name,
                "provider": model.provider,
                "base_url": model.base_url,
                "api_key": model.api_key,
                "model_settings": model.model_settings or {}
            }

        except Exception as e:
            logger.error("获取模型配置失败", extra={"error": str(e)})
            return None

    def create_image_generation_provider(self, model_config: Dict[str, Any]):
        """创建图片生成提供商"""
        try:
            from app.core.image_generation import ImageProviderFactory

            # 映射provider名称到图片生成提供商
            provider_mapping = {
                'openai': 'openai',
                'opencompatible': 'openai_compatible',
                'gemini': 'gemini',
                'qwen': 'qwen',
                'tongyi': 'qwen',
                'volcengine': 'volcengine_ark',
                'doubao': 'volcengine_ark',
                'midjourney': 'midjourney',
                'stable_diffusion': 'stable_diffusion'
            }

            image_provider_name = provider_mapping.get(
                model_config["provider"].lower(), 'openai'
            )

            # 创建模型配置对象
            config_obj = type('ModelConfig', (), {
                'name': model_config["ai_model_name"],
                'provider': image_provider_name,
                'base_url': model_config["base_url"],
                'api_key': model_config["api_key"],
                'model_settings': model_config["model_settings"]
            })()

            # 使用提供商工厂创建提供商实例
            provider = ImageProviderFactory.create_provider(config_obj)

            logger.info("图片生成提供商创建成功", extra={
                "provider_type": type(provider).__name__
            })

            return provider

        except Exception as e:
            logger.error("创建图片生成提供商失败", extra={"error": str(e)})
            return None