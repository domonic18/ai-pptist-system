"""
标注Schema定义
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class SlideDataSchema(BaseModel):
    """幻灯片数据Schema"""
    slide_id: str
    screenshot: str
    elements: List[Dict[str, Any]]


class ModelConfigSchema(BaseModel):
    """模型配置Schema"""
    model_id: str
    multimodal_enabled: bool = True


class ExtractionConfigSchema(BaseModel):
    """提取配置Schema"""
    screenshot_quality: str = "high"
    include_element_data: bool = True


class AnnotationStartRequest(BaseModel):
    """启动标注请求"""
    slides: List[Dict[str, Any]]
    model_config: Optional[ModelConfigSchema] = None
    extraction_config: Optional[ExtractionConfigSchema] = None


class PageTypeResult(BaseModel):
    """页面类型结果"""
    type: str
    confidence: float
    reason: str


class LayoutTypeResult(BaseModel):
    """布局类型结果"""
    type: str
    confidence: float
    reason: str


class ElementAnnotationResult(BaseModel):
    """元素标注结果"""
    element_id: str
    type: str
    confidence: float
    reason: str


class SlideAnnotationResult(BaseModel):
    """幻灯片标注结果"""
    slide_id: str
    page_type: PageTypeResult
    layout_type: LayoutTypeResult
    element_annotations: List[ElementAnnotationResult]
    overall_confidence: float


class AnnotationProgressResponse(BaseModel):
    """标注进度响应"""
    task_id: str
    status: str
    progress: Dict[str, Any]
    current_page: int
    estimated_remaining_time: int


class AnnotationResultResponse(BaseModel):
    """标注结果响应"""
    task_id: str
    status: str
    results: List[SlideAnnotationResult]
    statistics: Dict[str, Any]