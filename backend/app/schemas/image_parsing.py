"""
图片解析相关的Pydantic数据模型
用于API请求和响应的数据验证和序列化
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# 基础数据模型
# ============================================================================

class BoundingBox(BaseModel):
    """边界框坐标"""
    x: int = Field(..., description="左上角X坐标（像素）")
    y: int = Field(..., description="左上角Y坐标（像素）")
    width: int = Field(..., description="宽度（像素）")
    height: int = Field(..., description="高度（像素）")


class FontInfo(BaseModel):
    """字体信息"""
    size: int = Field(..., description="字体大小（像素）")
    family: str = Field(default="Microsoft YaHei", description="字体族")
    weight: str = Field(default="normal", description="字重：normal 或 bold")
    color: str = Field(default="#000000", description="字体颜色（十六进制）")
    align: str = Field(default="left", description="对齐方式：left, center, right")


class TextRegion(BaseModel):
    """文字区域"""
    id: str = Field(..., description="区域唯一标识")
    text: str = Field(..., description="识别的文字内容")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    confidence: float = Field(..., ge=0, le=1, description="识别置信度 0-1")
    font: Optional[FontInfo] = Field(None, description="字体信息（可选）")


class ParseMetadata(BaseModel):
    """解析元数据"""
    parse_time: int = Field(..., description="解析耗时（毫秒）")
    ocr_engine: str = Field(..., description="OCR引擎名称")
    text_count: int = Field(..., description="识别的文字数量")
    image_width: Optional[int] = Field(None, description="OCR识别所用原图宽度（像素）")
    image_height: Optional[int] = Field(None, description="OCR识别所用原图高度（像素）")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


# ============================================================================
# 请求模型
# ============================================================================

class ParseRequest(BaseModel):
    """解析请求"""
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: str = Field(..., description="图片COS Key")


class ParseOptions(BaseModel):
    """解析选项（预留扩展）"""
    # MVP阶段使用百度云OCR，无需传递额外参数
    # 未来可扩展：language, detect_tables 等选项


# ============================================================================
# 响应模型
# ============================================================================

class ParseTaskResponse(BaseModel):
    """解析任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    estimated_time: int = Field(default=5, description="预计耗时（秒）")
    message: Optional[str] = Field(None, description="提示消息")


class ParseStatusResponse(BaseModel):
    """解析状态响应（完成时包含完整结果）"""
    task_id: str = Field(..., description="任务ID")
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: Optional[str] = Field(None, description="图片COS Key")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="进度 0-100")
    current_step: Optional[str] = Field(None, description="当前处理步骤")
    text_regions: Optional[List[TextRegion]] = Field(None, description="文字区域列表（完成时）")
    metadata: Optional[ParseMetadata] = Field(None, description="解析元数据（完成时）")
    message: Optional[str] = Field(None, description="提示消息")


class ImageParseResult(BaseModel):
    """图片解析结果（完整版）"""
    task_id: str = Field(..., description="任务ID")
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: Optional[str] = Field(None, description="图片COS Key")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="进度 0-100")
    text_regions: List[TextRegion] = Field(..., description="文字区域列表")
    metadata: Optional[ParseMetadata] = Field(None, description="解析元数据（任务完成时存在）")
