"""
AI模型管理服务（统一架构）
处理AI模型的CRUD操作和业务逻辑
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)


class ManagementService:
    """AI模型管理服务（统一架构）"""

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
                "ai_model_name": model.ai_model_name,
                "base_url": model.base_url,
                "api_key": model.api_key,
                "capabilities": model.capabilities or [],
                "provider_mapping": model.provider_mapping or {},
                "parameters": model.parameters or {},
                "max_tokens": model.max_tokens,
                "context_window": model.context_window,
                "is_enabled": model.is_enabled,
                "is_default": model.is_default,
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
        capability: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取模型列表
        
        Args:
            enabled_only: 是否只返回启用的模型
            capability: 按能力过滤（如 'chat', 'image_gen'等）
        """
        try:
            models = await self.repository.list_models(
                enabled_only=enabled_only,
                capability=capability
            )
            return [self._model_to_dict(model) for model in models]
        except Exception as e:
            logger.error(
                "获取AI模型列表失败",
                extra={
                    "error": str(e),
                    "capability": capability
                }
            )
            return []

    async def get_default_model(self, capability: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取默认模型

        Args:
            capability: 如果指定，返回支持该能力的默认模型
        """
        try:
            model = await self.repository.get_default_model(capability=capability)
            return self._model_to_dict(model) if model else None
        except Exception as e:
            logger.error(
                "获取默认AI模型失败",
                extra={
                    "error": str(e),
                    "capability": capability
                }
            )
            return None

    async def get_default_model_for_use(self, capability: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取默认模型（内部使用，包含api_key）

        与 get_default_model 的区别在于此方法返回包含 api_key 的完整配置，
        仅用于内部服务调用，不对外暴露。

        Args:
            capability: 如果指定，返回支持该能力的默认模型

        Returns:
            包含 api_key 的模型配置字典
        """
        try:
            model = await self.repository.get_default_model(capability=capability)
            if not model:
                return None

            return {
                "id": model.id,
                "name": model.name,
                "ai_model_name": model.ai_model_name,
                "base_url": model.base_url,
                "api_key": model.api_key,  # 包含敏感信息
                "capabilities": model.capabilities or [],
                "provider_mapping": model.provider_mapping or {},
                "parameters": model.parameters or {},
                "max_tokens": model.max_tokens,
                "context_window": model.context_window,
                "is_enabled": model.is_enabled,
                "is_default": model.is_default,
                "created_at": model.created_at,
                "updated_at": model.updated_at
            }
        except Exception as e:
            logger.error(
                "获取默认AI模型失败（内部使用）",
                extra={
                    "error": str(e),
                    "capability": capability
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
                ai_model_name=model_data["ai_model_name"],
                base_url=model_data.get("base_url"),
                api_key=model_data.get("api_key", ""),
                capabilities=model_data.get("capabilities", []),
                provider_mapping=model_data.get("provider_mapping", {}),
                parameters=model_data.get("parameters", {}),
                max_tokens=model_data.get("max_tokens", 8192),
                context_window=model_data.get("context_window", 16384),
                is_enabled=model_data.get("is_enabled", True),
                is_default=model_data.get("is_default", False)
            )

            logger.info(
                "成功创建AI模型",
                extra={
                    "model_id": new_model.id,
                    "model_name": new_model.name,
                    "capabilities": new_model.capabilities
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
            
            # 基本字段
            for field in ["name", "ai_model_name", "base_url", "api_key"]:
                if field in update_data:
                    update_fields[field] = update_data[field]
            
            # 统一架构字段
            for field in ["capabilities", "provider_mapping", "parameters", 
                         "max_tokens", "context_window"]:
                if field in update_data:
                    update_fields[field] = update_data[field]
            
            # 状态字段
            for field in ["is_enabled", "is_default"]:
                if field in update_data:
                    update_fields[field] = update_data[field]

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
        """将模型对象转换为字典（统一架构）"""
        return {
            "id": model.id,
            "name": model.name,
            "ai_model_name": model.ai_model_name,
            "base_url": model.base_url,
            "capabilities": model.capabilities or [],
            "provider_mapping": model.provider_mapping or {},
            "parameters": model.parameters or {},
            "max_tokens": model.max_tokens,
            "context_window": model.context_window,
            "is_enabled": model.is_enabled,
            "is_default": model.is_default,
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

            models = await self.repository.get_models_by_capability('image_gen')

            result = []
            for model in models:
                result.append({
                    "id": model.id,
                    "name": model.name,
                    "ai_model_name": model.ai_model_name,
                    "provider": model.get_provider_for_capability('image_gen'),
                    "is_enabled": model.is_enabled,
                    "is_default": model.is_default,
                    "base_url": model.base_url,
                    "parameters": model.parameters or {}
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

            # 如果找不到，尝试通过ai_model_name字段查找
            if not model:
                all_models = await self.repository.get_models_by_capability('image_gen')
                model = next((m for m in all_models if m.ai_model_name == model_name), None)

            if not model:
                logger.error("模型不存在", extra={
                    "model_name": model_name,
                    "note": "请检查前端传递的model_name是否与数据库中的ai_model_name字段匹配"
                })
                return None

            if not model.has_capability('image_gen'):
                logger.error("模型不支持图片生成", extra={
                    "model_name": model_name,
                    "capabilities": model.capabilities
                })
                return None

            return {
                "id": model.id,
                "name": model.name,
                "ai_model_name": model.ai_model_name,
                "provider": model.get_provider_for_capability('image_gen'),
                "base_url": model.base_url,
                "api_key": model.api_key,
                "parameters": model.parameters or {}
            }

        except Exception as e:
            logger.error("获取模型配置失败", extra={"error": str(e)})
            return None

    def create_image_generation_provider(self, model_config: Dict[str, Any]):
        """创建图片生成提供商（使用统一架构）"""
        try:
            from app.core.ai.factory import AIProviderFactory
            from app.core.ai.models import ModelCapability
            from app.core.ai.config import ModelConfig as AIModelConfig

            # 使用新架构：从provider_mapping获取image_gen的provider
            provider_mapping = model_config.get("provider_mapping", {})
            if not provider_mapping or "image_gen" not in provider_mapping:
                logger.error("模型配置缺少image_gen的provider映射")
                return None

            # 创建ModelConfig对象
            ai_model_config = AIModelConfig(
                model_id=model_config.get("id", ""),
                model_name=model_config["ai_model_name"],
                api_key=model_config["api_key"],
                base_url=model_config.get("base_url"),
                capabilities=model_config.get("capabilities", []),
                provider_mapping=provider_mapping,
                parameters=model_config.get("parameters", {}),
                max_tokens=model_config.get("max_tokens"),
                context_window=model_config.get("context_window")
            )

            # 使用统一的AIProviderFactory创建提供商实例
            provider = AIProviderFactory.create(
                model_config=ai_model_config,
                capability=ModelCapability.IMAGE_GEN
            )

            logger.info("图片生成提供商创建成功", extra={
                "provider_type": type(provider).__name__,
                "provider_name": provider_mapping.get("image_gen")
            })

            return provider

        except Exception as e:
            logger.error("创建图片生成提供商失败", extra={"error": str(e)})
            return None
