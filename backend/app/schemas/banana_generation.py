"""
Banana PPT生成相关的Pydantic数据模型
用于文生图PPT生成功能的API请求和响应验证
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# 请求模型
# ============================================================================

class OutlineData(BaseModel):
    """PPT大纲数据"""
    title: str = Field(..., description="PPT主标题")
    slides: List[Dict[str, Any]] = Field(..., description="幻灯片列表，每个包含title和points")


class SplitOutlineRequest(BaseModel):
    """大纲拆分请求"""
    content: str = Field(..., description="原始Markdown大纲内容")
    ai_model_id: str = Field(..., description="用于拆分的AI模型ID")


class CanvasSize(BaseModel):
    """画布尺寸"""
    width: float = Field(default=1920, description="画布宽度")
    height: float = Field(default=1080, description="画布高度")


class GenerateBatchSlidesRequest(BaseModel):
    """批量生成PPT请求"""
    outline: OutlineData = Field(..., description="PPT大纲数据")
    template_id: Optional[str] = Field(None, description="模板ID（与custom_template_url二选一）")
    custom_template_url: Optional[str] = Field(None, description="自定义模板图片URL（与template_id二选一）")
    generation_model: str = Field(default="gemini-3-pro-image-preview", description="生成模型名称")
    canvas_size: CanvasSize = Field(default_factory=CanvasSize, description="画布尺寸")


class RegenerateSlideRequest(BaseModel):
    """重新生成单张幻灯片请求"""
    task_id: str = Field(..., description="任务ID")
    slide_index: int = Field(..., ge=0, description="幻灯片索引")


# ============================================================================
# 响应模型
# ============================================================================

class SlideGenerationResult(BaseModel):
    """单页生成结果"""
    index: int = Field(..., description="幻灯片索引")
    title: Optional[str] = Field(None, description="标题")
    status: str = Field(..., description="状态: pending|processing|completed|failed")
    image_url: Optional[str] = Field(None, description="COS图片URL")
    cos_path: Optional[str] = Field(None, description="COS存储路径")
    generation_time: Optional[float] = Field(None, description="生成耗时(秒)")
    error: Optional[str] = Field(None, description="错误信息")


class GenerationProgress(BaseModel):
    """生成进度信息"""
    total: int = Field(..., description="总幻灯片数")
    completed: int = Field(..., ge=0, description="已完成数量")
    failed: int = Field(..., ge=0, description="失败数量")
    pending: int = Field(..., ge=0, description="待处理数量")


class GenerationStatusResponse(BaseModel):
    """生成状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: Dict[str, int] = Field(..., description="进度信息: {total, completed, failed, pending}")
    slides: List[SlideGenerationResult] = Field(..., description="每页状态列表")


class GenerateBatchSlidesResponse(BaseModel):
    """批量生成响应"""
    task_id: str = Field(..., description="生成任务ID")
    celery_task_id: str = Field(..., description="Celery任务ID")
    total_slides: int = Field(..., description="总幻灯片数")
    status: str = Field(default="processing", description="任务状态")


class TemplateInfo(BaseModel):
    """模板信息"""
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    thumbnail_url: str = Field(..., description="缩略图URL")
    aspect_ratio: str = Field(..., description="宽高比: 16:9|4:3")
    type: str = Field(..., description="类型: system|user")


class TemplateListResponse(BaseModel):
    """模板列表响应"""
    templates: List[TemplateInfo] = Field(..., description="模板列表")


class StopGenerationResponse(BaseModel):
    """停止生成响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    completed_slides: int = Field(..., description="已完成的幻灯片数")
    total_slides: int = Field(..., description="总幻灯片数")


class RegenerateSlideResponse(BaseModel):
    """重新生成单张幻灯片响应"""
    slide_index: int = Field(..., description="幻灯片索引")
    status: str = Field(..., description="状态")
    celery_task_id: str = Field(..., description="Celery任务ID")
