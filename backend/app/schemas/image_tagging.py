"""
图片标签相关的 Pydantic 模型
用于图片标签操作的数据验证和序列化
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ImageTagAdd(BaseModel):
    """图片标签添加模型"""
    tags: List[str] = Field(..., description="要添加的标签列表", min_items=1)


class ImageTagUpdate(BaseModel):
    """图片标签更新模型"""
    tags: List[str] = Field(..., description="更新后的标签列表")


class ImageTagDelete(BaseModel):
    """图片标签删除请求模型"""
    tags: Optional[List[str]] = Field(None, description="要删除的标签列表，为空则删除所有标签")


class ImageTagResponse(BaseModel):
    """图片标签响应模型"""
    image_id: str = Field(..., description="图片ID")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    total: int = Field(default=0, description="标签总数")


class BatchImageTagOperation(BaseModel):
    """批量图片标签操作请求模型"""
    image_ids: List[str] = Field(..., description="图片ID列表", min_items=1)
    tags: List[str] = Field(..., description="标签列表", min_items=1)
    operation: Literal["add", "remove", "replace"] = Field(
        default="add",
        description="操作类型：add-添加, remove-删除, replace-替换"
    )

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
    """批量图片标签操作响应模型"""
    success_count: int = Field(..., description="成功操作的数量")
    failed_count: int = Field(..., description="失败操作的数量")
    results: List[dict] = Field(default_factory=list, description="操作结果列表")
    errors: List[dict] = Field(default_factory=list, description="错误列表")

    class Config:
        extra = "allow"  # 允许额外的字段
        from_attributes = True


class ImageSearchByTagsResponse(BaseModel):
    """根据标签搜索图片响应模型"""
    items: List[dict] = Field(default_factory=list, description="图片列表")
    total: int = Field(..., description="总记录数")
    skip: int = Field(..., description="跳过的记录数")
    limit: int = Field(..., description="返回的记录数")
    query_tags: List[str] = Field(default_factory=list, description="搜索标签")
