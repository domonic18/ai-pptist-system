"""
图片搜索相关Schema定义
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ImageSearchRequest(BaseModel):
    """图片搜索请求"""
    prompt: str = Field(..., min_length=1, max_length=500, description="搜索提示词")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制")
    match_threshold: int = Field(70, ge=50, le=100, description="匹配精度阈值（百分比）")

    class Config:
        from_attributes = True


class ImageSearchResult(BaseModel):
    """图片搜索结果"""
    id: str = Field(..., description="图片ID")
    prompt: str = Field(..., description="生成提示词")
    model_name: str = Field(..., description="模型名称")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    file_size: Optional[int] = Field(None, description="文件大小")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    cos_key: Optional[str] = Field(None, description="COS对象键")
    url: Optional[str] = Field(None, description="图片访问URL")
    match_type: str = Field(..., description="匹配类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="匹配置信度")

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class ImageSearchResponse(BaseModel):
    """图片搜索响应"""
    success: bool = Field(..., description="搜索是否成功")
    results: List[ImageSearchResult] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="结果总数")
    error: Optional[str] = Field(None, description="错误信息")

    class Config:
        from_attributes = True


class TagSearchRequest(BaseModel):
    """标签搜索请求"""
    tags: List[str] = Field(..., description="搜索标签列表")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制")

    class Config:
        from_attributes = True


class SearchStatistics(BaseModel):
    """搜索统计信息"""
    total_images: int = Field(..., description="总图片数")
    unique_tags: int = Field(..., description="唯一标签数")
    tags_list: List[str] = Field(..., description="标签列表")
    has_search_history: bool = Field(..., description="是否有搜索历史")

    class Config:
        from_attributes = True