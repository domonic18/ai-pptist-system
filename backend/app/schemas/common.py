"""
通用Pydantic模型
用于标准化API响应
"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel


class StandardResponse(BaseModel):
    """标准化响应模型"""
    status: str = "success"
    message: str = ""
    data: Optional[Any] = None


class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    message: str = "操作失败"
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """分页参数模型"""
    skip: int = 0
    limit: int = 20


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool