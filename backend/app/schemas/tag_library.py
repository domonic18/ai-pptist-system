"""
标签库相关的 Pydantic 模型
用于标签库的数据验证和序列化
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """标签基础模型"""
    name: str = Field(..., description="标签名称")
    description: Optional[str] = Field(None, description="标签描述")


class TagCreate(TagBase):
    """标签创建模型"""
    pass


class TagResponse(TagBase):
    """标签响应模型"""
    id: str = Field(..., description="标签ID")
    usage_count: int = Field(default=0, description="使用次数")
    created_at: str = Field(..., description="创建时间")

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class TagSearchParams(BaseModel):
    """标签搜索参数模型"""
    query: Optional[str] = Field(None, description="搜索关键词")
    page: int = Field(default=1, ge=1, description="页码")
    limit: int = Field(default=20, ge=1, le=100, description="每页记录数")
    sort_by: str = Field(default="usage_count", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


class TagListResponse(BaseModel):
    """标签列表响应模型"""
    items: List[TagResponse] = Field(default_factory=list, description="标签列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页记录数")
    total_pages: int = Field(..., description="总页数")


class PopularTagResponse(BaseModel):
    """热门标签响应模型"""
    tags: List[TagResponse] = Field(default_factory=list, description="热门标签列表")
    total: int = Field(..., description="总记录数")
    limit: int = Field(..., description="返回数量限制")


class TagSearchResponse(BaseModel):
    """标签搜索响应模型"""
    tags: List[TagResponse] = Field(default_factory=list, description="搜索结果")
    total: int = Field(..., description="总记录数")
    query: str = Field(..., description="搜索关键词")
    limit: int = Field(..., description="返回数量限制")
