"""
布局优化API端点（轻路由）
负责参数验证、调用Handler、返回标准响应
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.layout_optimization import (
    LayoutOptimizationRequest,
    LayoutOptimizationResponseData
)
from app.schemas.common import StandardResponse
from app.services.layout.layout_optimization_handler import LayoutOptimizationHandler


def _remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归移除字典中的None值
    
    Args:
        data: 输入字典
        
    Returns:
        Dict[str, Any]: 移除None值后的字典
    """
    cleaned = {}
    for key, value in data.items():
        if value is None:
            continue
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            cleaned_nested = _remove_none_values(value)
            if cleaned_nested:  # 只保留非空字典
                cleaned[key] = cleaned_nested
        elif isinstance(value, list):
            # 处理数组，移除None元素
            cleaned_list = []
            for item in value:
                if item is None:
                    continue
                elif isinstance(item, dict):
                    cleaned_item = _remove_none_values(item)
                    if cleaned_item:
                        cleaned_list.append(cleaned_item)
                else:
                    cleaned_list.append(item)
            if cleaned_list:  # 只保留非空数组
                cleaned[key] = cleaned_list
        else:
            cleaned[key] = value
    return cleaned

# 注意：使用空字符串""作为根路径，prefix在router.py中统一管理
router = APIRouter(tags=["布局优化"])


@router.post(
    "/optimize",  # 完整路径：/api/v1/layout/optimize
    response_model=StandardResponse,
    summary="优化幻灯片布局",
    description="使用LLM智能优化幻灯片的排版布局，保持内容不变"
)
async def optimize_slide_layout(
    request: LayoutOptimizationRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    优化幻灯片布局的API端点

    Args:
        request: 布局优化请求（Pydantic自动验证）
        db: 数据库会话

    Returns:
        StandardResponse: 标准响应格式
            - status: "success" | "error" | "warning"
            - message: 响应消息
            - data: LayoutOptimizationResponseData | None
            - error_code: 错误码（可选）
            - error_details: 错误详情（可选）
    """
    # 调用Handler处理业务
    handler = LayoutOptimizationHandler(db)
    result = await handler.handle_optimize_layout(request)

    # 手动序列化数据，排除None值以避免前端处理问题
    # 将Pydantic对象转换为字典时使用exclude_none=True
    # 注意：关键字段（如viewBox）已在HTML解析器中确保有值，这里只清理非必要的None值
    result_dict = result.model_dump(exclude_none=True)

    # 递归清理elements数组中每个元素的None值
    if "elements" in result_dict and isinstance(result_dict["elements"], list):
        result_dict["elements"] = [
            _remove_none_values(el) if isinstance(el, dict) else el
            for el in result_dict["elements"]
        ]

    # 返回标准响应
    return StandardResponse(
        status="success",
        message="布局优化完成",
        data=result_dict
    )