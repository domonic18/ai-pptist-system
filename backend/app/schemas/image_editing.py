"""
图片编辑相关的Pydantic数据模型
用于混合OCR识别和文字去除功能的API请求和响应验证
"""

from typing import Optional, List, Dict, Any
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
    size: float = Field(..., description="字体大小（像素）")
    family: str = Field(default="Microsoft YaHei", description="字体族")
    weight: str = Field(default="normal", description="字重：normal 或 bold")
    color: str = Field(default="#000000", description="字体颜色（十六进制）")
    align: Optional[str] = Field(None, description="对齐方式：left, center, right")


# ============================================================================
# 传统OCR结果
# ============================================================================

class TraditionalOCRRegion(BaseModel):
    """传统OCR识别结果区域"""
    text: str = Field(..., description="识别的文字内容")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    confidence: float = Field(..., ge=0, le=1, description="识别置信度 0-1")


class TraditionalOCRResult(BaseModel):
    """传统OCR识别结果"""
    engine: str = Field(..., description="OCR引擎名称：baidu_ocr, tencent_ocr等")
    regions: List[TraditionalOCRRegion] = Field(default_factory=list, description="识别的文字区域列表")
    parse_time_ms: int = Field(..., description="解析耗时（毫秒）")
    text_count: int = Field(..., description="识别的文字数量")


# ============================================================================
# 多模态OCR结果
# ============================================================================

class MultimodalOCRRegion(BaseModel):
    """多模态OCR识别结果区域"""
    text: str = Field(..., description="识别的文字内容")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    confidence: float = Field(..., ge=0, le=1, description="识别置信度 0-1")
    font: FontInfo = Field(..., description="字体信息")


class MultimodalOCRResult(BaseModel):
    """多模态OCR识别结果"""
    model: str = Field(..., description="模型名称：gpt-4o, claude-3.5-vision等")
    regions: List[MultimodalOCRRegion] = Field(default_factory=list, description="识别的文字区域列表")
    parse_time_ms: int = Field(..., description="解析耗时（毫秒）")
    text_count: int = Field(..., description="识别的文字数量")


# ============================================================================
# 混合OCR结果
# ============================================================================

class HybridTextRegion(BaseModel):
    """融合后的文字区域"""
    id: str = Field(..., description="区域唯一标识")
    text: str = Field(..., description="文字内容")
    bbox: BoundingBox = Field(..., description="边界框坐标")
    confidence: float = Field(..., ge=0, le=1, description="识别置信度 0-1")
    font: FontInfo = Field(..., description="字体信息")
    color: str = Field(..., description="文字颜色（十六进制）")
    source: str = Field(..., description="数据来源：traditional, multimodal, merged")


class HybridOCRMetadata(BaseModel):
    """混合OCR元数据"""
    traditional_ocr_engine: str = Field(..., description="使用的传统OCR引擎")
    multimodal_model: str = Field(..., description="使用的多模态模型")
    parse_time_ms: int = Field(..., description="总解析耗时（毫秒）")
    traditional_time_ms: int = Field(..., description="传统OCR耗时（毫秒）")
    multimodal_time_ms: int = Field(..., description="多模态OCR耗时（毫秒）")
    merge_time_ms: int = Field(..., description="融合耗时（毫秒）")
    text_count: int = Field(..., description="融合后文字数量")
    traditional_count: int = Field(..., description="传统OCR识别数量")
    multimodal_count: int = Field(..., description="多模态识别数量")
    merged_count: int = Field(..., description="融合后数量")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: datetime = Field(..., description="完成时间")


class HybridOCRResult(BaseModel):
    """混合OCR识别结果"""
    task_id: str = Field(..., description="任务ID")
    slide_id: str = Field(..., description="幻灯片ID")
    original_cos_key: str = Field(..., description="原始图片COS Key")
    text_regions: List[HybridTextRegion] = Field(default_factory=list, description="融合后的文字区域列表")
    metadata: HybridOCRMetadata = Field(..., description="元数据")


# ============================================================================
# 文字去除结果
# ============================================================================

class TextRemovalResult(BaseModel):
    """文字去除结果"""
    original_cos_key: str = Field(..., description="原始图片COS Key")
    edited_cos_key: str = Field(..., description="编辑后的图片COS Key")
    processing_time_ms: int = Field(..., description="处理耗时（毫秒）")
    model_used: str = Field(..., description="使用的模型：dall-e-3, stable-diffusion等")
    prompt_used: str = Field(..., description="使用的提示词")
    created_at: datetime = Field(..., description="创建时间")


# ============================================================================
# 编辑任务元数据
# ============================================================================

class EditingTaskMetadata(BaseModel):
    """编辑任务元数据"""
    total_time_ms: int = Field(..., description="总处理耗时（毫秒）")
    ocr_time_ms: int = Field(..., description="OCR识别耗时（毫秒）")
    removal_time_ms: Optional[int] = Field(None, description="文字去除耗时（毫秒）")
    text_count: int = Field(..., description="识别的文字数量")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


# ============================================================================
# 请求模型
# ============================================================================

class ParseAndRemoveRequest(BaseModel):
    """一步完成：OCR识别 + 文字去除请求"""
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: str = Field(..., description="图片COS Key")


class HybridOCRParseRequest(BaseModel):
    """仅混合OCR识别请求"""
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: str = Field(..., description="图片COS Key")


class RemoveTextRequest(BaseModel):
    """仅去除文字请求"""
    slide_id: str = Field(..., description="幻灯片ID")
    cos_key: str = Field(..., description="原始图片COS Key")
    ocr_task_id: str = Field(..., description="OCR任务ID（用于获取文字位置）")


# ============================================================================
# 响应模型
# ============================================================================

class EditingTaskResponse(BaseModel):
    """编辑任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    estimated_time: int = Field(default=15, description="预计耗时（秒）")
    message: Optional[str] = Field(None, description="提示消息")


class EditingStatusResponse(BaseModel):
    """编辑状态响应"""
    task_id: str = Field(..., description="任务ID")
    slide_id: str = Field(..., description="幻灯片ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="进度 0-100")
    current_step: Optional[str] = Field(None, description="当前处理步骤")
    message: Optional[str] = Field(None, description="提示消息")
    ocr_result: Optional[HybridOCRResult] = Field(None, description="OCR识别结果（完成时）")
    edited_image: Optional[TextRemovalResult] = Field(None, description="编辑后的图片信息（完成时）")


class EditingResultResponse(BaseModel):
    """编辑完整结果响应"""
    task_id: str = Field(..., description="任务ID")
    slide_id: str = Field(..., description="幻灯片ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., ge=0, le=100, description="进度 0-100")
    ocr_result: Optional[HybridOCRResult] = Field(None, description="OCR识别结果")
    edited_image: Optional[TextRemovalResult] = Field(None, description="编辑后的图片信息")
    metadata: Optional[EditingTaskMetadata] = Field(None, description="任务元数据")
    error_message: Optional[str] = Field(None, description="错误信息")
