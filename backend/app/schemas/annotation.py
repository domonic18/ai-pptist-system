"""
标注Schema定义
"""

from pydantic import BaseModel
from typing import List, Dict, Any


class SlideDataSchema(BaseModel):
    """幻灯片数据Schema"""
    slide_id: str
    screenshot: str
    elements: List[Dict[str, Any]]


class SingleAnnotationRequest(BaseModel):
    """单张幻灯片标注请求"""
    slide: Dict[str, Any]
    model_id: str


class BatchAnnotationRequest(BaseModel):
    """批量幻灯片标注请求"""
    slides: List[Dict[str, Any]]
    model_id: str
