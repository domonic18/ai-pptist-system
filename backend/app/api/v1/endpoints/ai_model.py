"""
AI模型管理API端点
负责AI模型的配置、管理和测试
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.common import StandardResponse
from app.schemas.ai_model import (
    AIModelCreate, AIModelUpdate, AIModelResponse, AIModelListResponse
)
from app.services.ai_model.management.handler import ManagementHandler
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["AI模型管理"])


@router.get(
    "",
    response_model=StandardResponse,
    summary="获取AI模型列表",
    description="获取所有配置的AI模型列表（统一架构）"
)
async def list_ai_models(
    enabled_only: bool = True,
    capability: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取AI模型列表（统一架构）

    Args:
        enabled_only: 是否只返回启用的模型
        capability: 按能力过滤（如 'chat', 'image_gen'等，None表示不过滤）
        db: 数据库会话

    Returns:
        StandardResponse: 包含模型列表的标准化响应
    """
    handler = ManagementHandler(db)
    result = await handler.handle_list_models(
        enabled_only=enabled_only,
        capability=capability
    )

    # 转换为响应模型
    model_responses = [AIModelResponse.model_validate(model) for model in result["items"]]

    logger.info(
        "成功获取AI模型列表",
        operation="list_models_success",
        total_models=result["total"],
        enabled_only=enabled_only,
        capability=capability
    )

    return StandardResponse(
        status="success",
        message=f"成功获取 {len(model_responses)} 个AI模型",
        data={
            "items": [model.model_dump() for model in model_responses],
            "total": result["total"]
        }
    )


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
    handler = ManagementHandler(db)
    model = await handler.handle_get_model_for_edit(model_id)

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
    handler = ManagementHandler(db)
    updated_model = await handler.handle_update_model(model_id, update_data.model_dump())

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
    handler = ManagementHandler(db)
    await handler.handle_delete_model(model_id)

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
