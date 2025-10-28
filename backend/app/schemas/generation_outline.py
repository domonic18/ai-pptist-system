"""
大纲生成相关的Pydantic验证模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class OutlineSlide(BaseModel):
    """大纲幻灯片模型"""
    slide_index: int = Field(..., ge=0, description="幻灯片索引（从0开始）")
    title: str = Field(..., min_length=1, max_length=100, description="幻灯片标题")
    points: List[str] = Field(..., min_length=1, max_length=5, description="要点列表")
    slide_type: int = Field(..., ge=1, le=9, description="幻灯片类型（1-9）")
    needs_image: bool = Field(False, description="是否需要图片")

    @field_validator('points')
    @classmethod
    def validate_points(cls, v):
        """验证要点内容"""
        for point in v:
            if len(point.strip()) == 0:
                raise ValueError("要点内容不能为空")
            if len(point) > 200:
                raise ValueError("单个要点长度不能超过200字符")
        return v


class OutlineGenerationRequest(BaseModel):
    """大纲生成请求模型"""
    title: str = Field(..., min_length=1, max_length=200, description="演示文稿标题")
    input_content: Optional[str] = Field(None, description="输入内容或提示")
    slide_count: int = Field(10, ge=5, le=25, description="幻灯片数量")
    language: str = Field("zh-CN", description="输出语言")
    model_settings: Optional[Dict[str, Any]] = Field(None, description="模型配置")

    model_config = {
        "protected_namespaces": ()
    }


class OutlineGenerationResponse(BaseModel):
    """大纲生成响应模型"""
    outline: List[OutlineSlide]
    total_slides: int
    generation_time: Optional[float] = Field(None, description="生成耗时（秒）")
