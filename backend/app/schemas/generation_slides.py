"""
幻灯片生成相关的Pydantic验证模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SlidesGenerationRequest(BaseModel):
    """幻灯片生成请求模型"""
    content: str = Field(..., description="Markdown格式的大纲内容")
    language: str = Field("zh-CN", description="输出语言")
    style: str = Field("professional", description="演示文稿风格")
    model: Optional[str] = Field(None, description="模型名称")
    stream: Optional[bool] = Field(True, description="是否使用流式输出")

    class Config:
        protected_namespaces = ()


class SlideContent(BaseModel):
    """幻灯片内容模型"""
    type: str = Field(..., description="幻灯片类型")
    data: Dict[str, Any] = Field(..., description="幻灯片数据")


class SlidesGenerationResponse(BaseModel):
    """幻灯片生成响应模型"""
    slides: List[SlideContent]
    total_slides: int
    generation_time: Optional[float] = Field(None, description="生成耗时（秒）")
