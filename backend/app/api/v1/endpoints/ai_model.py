"""
AI模型管理API端点
负责AI模型的配置、管理和测试
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.common import StandardResponse
from app.schemas.ai_model import (
    AIModelCreate, AIModelUpdate, AIModelResponse, AIModelListResponse
)
from app.services.ai_model.management_handler import ManagementHandler
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["AI Model Management"])


@router.get(
    "",
    response_model=StandardResponse,
    summary="获取AI模型列表",
    description="获取所有配置的AI模型列表"
)
async def list_ai_models(
    enabled_only: bool = True,
    supports_image_generation: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取AI模型列表

    Args:
        enabled_only: 是否只返回启用的模型
        supports_image_generation: 是否只返回支持图片生成的模型（None表示不过滤）
        db: 数据库会话

    Returns:
        StandardResponse: 包含模型列表的标准化响应
    """
    try:
        handler = ManagementHandler(db)
        result = await handler.handle_list_models(
            enabled_only=enabled_only,
            supports_image_generation=supports_image_generation
        )

        # 转换为响应模型
        model_responses = [AIModelResponse.model_validate(model) for model in result["items"]]

        logger.info(
            "成功获取AI模型列表",
            operation="list_models_success",
            total_models=result["total"],
            enabled_only=enabled_only
        )

        return StandardResponse(
            status="success",
            message=f"成功获取 {len(model_responses)} 个AI模型",
            data={
                "items": [model.model_dump() for model in model_responses],
                "total": result["total"]
            }
        )

    except Exception as e:
        logger.error(
            "获取AI模型列表失败",
            operation="list_models_failed",
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        ) from e


@router.get(
    "/{model_id}",
    response_model=StandardResponse,
    summary="获取AI模型详情",
    description="获取指定AI模型的详细信息（包含API密钥等敏感信息）"
)
async def get_ai_model(
    model_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取AI模型详情

    Args:
        model_id: 模型ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含模型详情的标准化响应
    """
    try:
        handler = ManagementHandler(db)
        model = await handler.handle_get_model_for_edit(model_id)

        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        logger.info(
            "成功获取AI模型详情",
            operation="get_model_success",
            model_id=model_id,
            model_name=model["name"]
        )

        return StandardResponse(
            status="success",
            message="成功获取AI模型详情",
            data=model
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取AI模型详情失败",
            operation="get_model_failed",
            exception=e,
            model_id=model_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型详情失败: {str(e)}"
        ) from e

@router.post(
    "/models",
    response_model=StandardResponse,
    summary="创建AI模型",
    description="创建新的AI模型配置"
)
async def create_ai_model(
    model_data: AIModelCreate,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    创建AI模型配置

    Args:
        model_data: 模型创建数据
        db: 数据库会话

    Returns:
        StandardResponse: 创建结果的标准化响应
    """
    try:
        handler = ManagementHandler(db)
        new_model = await handler.handle_create_model(model_data.model_dump())

        logger.info(
            "成功创建AI模型",
            operation="create_model_success",
            model_id=new_model["id"],
            model_name=new_model["name"]
        )

        return StandardResponse(
            status="success",
            message="AI模型创建成功",
            data=AIModelResponse.model_validate(new_model).model_dump()
        )

    except ValueError as e:
        logger.warning(
            "创建AI模型参数错误",
            operation="create_model_validation_failed",
            exception=e,
            model_name=model_data.name
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(
            "创建AI模型失败",
            operation="create_model_failed",
            exception=e,
            model_name=model_data.name
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模型失败: {str(e)}"
        ) from e


@router.put(
    "/models/{model_id}",
    response_model=StandardResponse,
    summary="更新AI模型",
    description="更新指定的AI模型配置"
)
async def update_ai_model(
    model_id: str,
    update_data: AIModelUpdate,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    更新AI模型配置

    Args:
        model_id: 模型ID
        update_data: 模型更新数据
        db: 数据库会话

    Returns:
        StandardResponse: 更新结果的标准化响应
    """
    try:
        handler = ManagementHandler(db)
        updated_model = await handler.handle_update_model(model_id, update_data.model_dump())

        if not updated_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        logger.info(
            "成功更新AI模型",
            operation="update_model_success",
            model_id=model_id,
            model_name=updated_model["name"]
        )

        return StandardResponse(
            status="success",
            message="AI模型更新成功",
            data=AIModelResponse.model_validate(updated_model).model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "更新AI模型失败",
            operation="update_model_failed",
            exception=e,
            model_id=model_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新模型失败: {str(e)}"
        ) from e


@router.delete(
    "/models/{model_id}",
    response_model=StandardResponse,
    summary="删除AI模型",
    description="删除指定的AI模型配置"
)
async def delete_ai_model(
    model_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    删除AI模型配置

    Args:
        model_id: 模型ID
        db: 数据库会话

    Returns:
        StandardResponse: 删除结果的标准化响应
    """
    try:
        handler = ManagementHandler(db)
        success = await handler.handle_delete_model(model_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在"
            )

        logger.info(
            "成功删除AI模型",
            operation="delete_model_success",
            model_id=model_id
        )

        return StandardResponse(
            status="success",
            message="AI模型删除成功",
            data={"model_id": model_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "删除AI模型失败",
            operation="delete_model_failed",
            exception=e,
            model_id=model_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型失败: {str(e)}"
        ) from e


@router.get(
    "image-generation-models",
    response_model=StandardResponse,
    summary="获取支持图片生成的模型列表",
    description="获取支持图片生成的AI模型列表"
)
async def get_supported_image_generation_models(
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取支持图片生成的模型列表

    Args:
        db: 数据库会话

    Returns:
        StandardResponse: 支持图片生成的模型列表
    """
    try:
        handler = ManagementHandler(db)
        models = await handler.handle_get_supported_image_generation_models()

        return StandardResponse(
            status="success",
            message="成功获取支持图片生成的模型列表",
            data={
                "items": models,
                "total": len(models)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "获取支持图片生成的模型列表失败",
            operation="get_image_generation_models_failed",
            exception=e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取支持的模型列表失败"
        ) from e
