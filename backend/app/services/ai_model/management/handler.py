"""
AI模型管理业务处理器（统一架构）
处理AI模型的CRUD操作
"""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_model.management.service import ManagementService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ManagementHandler:
    """AI模型管理业务处理器（统一架构）"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.management_service = ManagementService(db)

    async def handle_list_models(
        self,
        enabled_only: bool = True,
        capability: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理获取模型列表请求
        
        Args:
            enabled_only: 是否只返回启用的模型
            capability: 按能力过滤（如 'chat', 'image_gen'等）
        """
        try:
            models = await self.management_service.list_models(
                enabled_only=enabled_only,
                capability=capability
            )

            return {
                "items": models,
                "total": len(models)
            }

        except Exception as e:
            logger.error(
                "获取AI模型列表失败",
                extra={
                    "error": str(e),
                    "capability": capability
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取模型列表失败: {str(e)}"
            ) from e

    async def handle_create_model(
        self,
        model_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理创建模型请求"""
        try:

            new_model = await self.management_service.create_model(model_data)


            return new_model

        except ValueError as e:
            logger.warning(
                "创建AI模型参数错误",
                extra={
                    "error": str(e),
                    "model_name": model_data.get("name")
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                "创建AI模型失败",
                extra={
                    "error": str(e),
                    "model_name": model_data.get("name")
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建模型失败: {str(e)}"
            ) from e

    async def handle_update_model(
        self,
        model_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理更新模型请求"""
        try:
            updated_model = await self.management_service.update_model(model_id, update_data)

            if not updated_model:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="模型不存在"
                )

            return updated_model

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "更新AI模型失败",
                extra={
                    "error": str(e),
                    "model_id": model_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新模型失败: {str(e)}"
            ) from e

    async def handle_delete_model(
        self,
        model_id: str
    ) -> bool:
        """处理删除模型请求"""
        try:

            success = await self.management_service.delete_model(model_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="模型不存在"
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "删除AI模型失败",
                extra={
                    "error": str(e),
                    "model_id": model_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除模型失败: {str(e)}"
            ) from e

    async def handle_get_model_for_edit(
        self,
        model_id: str
    ) -> Optional[Dict[str, Any]]:
        """处理获取模型详情用于编辑请求"""
        try:
            model = await self.management_service.get_model_for_edit(model_id)

            if not model:
                logger.warning(
                    "AI模型不存在",
                    extra={
                        "model_id": model_id
                    }
                )
                return None

            return model

        except Exception as e:
            logger.error(
                "获取AI模型详情失败",
                extra={
                    "error": str(e),
                    "model_id": model_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取模型详情失败: {str(e)}"
            ) from e

    async def handle_get_supported_image_generation_models(self) -> List[Dict[str, Any]]:
        """
        处理获取支持图片生成的模型列表请求

        Returns:
            List[Dict[str, Any]]: 支持图片生成的模型列表

        Raises:
            HTTPException: 请求处理失败时抛出HTTP异常
        """
        try:
            logger.info("处理获取支持图片生成的模型列表请求")

            models = await self.management_service.get_supported_image_generation_models()

            return models

        except Exception as e:
            logger.error(
                "获取支持图片生成的模型列表请求处理异常",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取支持的模型列表失败"
            )