"""
标签相关的Pydantic模型
用于数据验证和序列化
"""

from typing import List, Optional, Literal
from pydantic import BaseModel


class TagBase(BaseModel):
    """标签基础模型"""
    name: str
    description: Optional[str] = None


class TagCreate(TagBase):
    """标签创建模型"""
    pass


class TagResponse(TagBase):
    """标签响应模型"""
    id: str
    usage_count: int = 0
    created_at: str

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class TagListResponse(BaseModel):
    """标签列表响应模型"""
    tags: List[TagResponse]
    total: int
    skip: int
    limit: int


class ImageTagUpdate(BaseModel):
    """图片标签更新模型"""
    tags: List[str]


class ImageTagAdd(BaseModel):
    """图片标签添加模型"""
    tags: List[str]


class TagSearchParams(BaseModel):
    """标签搜索参数模型"""
    query: Optional[str] = None
    page: int = 1
    limit: int = 20
    sort_by: str = "usage_count"
    sort_order: str = "desc"


class PopularTagResponse(BaseModel):
    """热门标签响应模型"""
    tags: List[TagResponse]
    total: int
    limit: int


class ImageTagDelete(BaseModel):
    """图片标签删除请求"""
    tags: Optional[List[str]] = None  # 如果为None，删除所有标签


class BatchImageTagOperation(BaseModel):
    """批量图片标签操作请求"""
    image_ids: List[str]
    tags: List[str]
    operation: Literal["add", "remove", "replace"] = "add"

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_ids": ["img1", "img2", "img3"],
                "tags": ["风景", "自然"],
                "operation": "add"
            }
        }
    }


class BatchImageTagResponse(BaseModel):
    """批量图片标签操作响应"""
    success_count: int
    failed_count: int
    results: List[dict]
    errors: List[dict] = []

    class Config:
        extra = "allow"  # 允许额外的字段
        from_attributes = True