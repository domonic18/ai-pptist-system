"""
布局优化相关数据模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CanvasSize(BaseModel):
    """画布尺寸"""
    width: float = Field(..., gt=0, description="画布宽度")
    height: float = Field(..., gt=0, description="画布高度")


class OptimizationOptions(BaseModel):
    """优化选项"""
    keep_colors: bool = Field(default=False, description="保持原有颜色")
    keep_fonts: bool = Field(default=False, description="保持原有字体")
    style: str = Field(
        default="professional",
        pattern="^(professional|creative|minimal)$",
        description="优化风格"
    )


class ElementData(BaseModel):
    """元素数据"""
    id: str = Field(..., description="元素ID")
    type: str = Field(..., description="元素类型：text/shape/image等")
    left: float = Field(..., description="X坐标")
    top: float = Field(..., description="Y坐标")
    width: Optional[float] = Field(default=None, gt=0, description="宽度")
    height: Optional[float] = Field(default=None, gt=0, description="高度")
    rotate: float = Field(default=0, description="旋转角度")

    # 可选属性（根据type不同而不同）
    content: Optional[str] = None
    defaultFontName: Optional[str] = None
    defaultColor: Optional[str] = None
    lineHeight: Optional[float] = None
    fill: Optional[str] = None
    outline: Optional[Dict[str, Any]] = None
    text: Optional[Dict[str, Any]] = None
    src: Optional[str] = None
    fixedRatio: Optional[bool] = None
    radius: Optional[float] = Field(default=None, ge=0, description="圆角半径")

    # 新增样式属性
    shadow: Optional[Dict[str, Any]] = Field(
        default=None,
        description="阴影样式：color, h, v, blur, spread"
    )
    opacity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="透明度（0.0-1.0）"
    )
    flipH: Optional[bool] = Field(
        default=None,
        description="水平翻转"
    )
    flipV: Optional[bool] = Field(
        default=None,
        description="垂直翻转"
    )

    # 文字特有属性
    fontSize: Optional[float] = Field(
        default=None,
        description="字体大小"
    )
    fontWeight: Optional[str] = Field(
        default=None,
        description="字体粗细"
    )
    textAlign: Optional[str] = Field(
        default=None,
        description="文本对齐方式"
    )
    wordSpace: Optional[float] = Field(
        default=None,
        description="字间距"
    )
    paragraphSpace: Optional[float] = Field(
        default=None,
        description="段间距"
    )

    # 图片特有属性
    filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="滤镜效果"
    )


class LayoutOptimizationRequest(BaseModel):
    """布局优化请求"""
    slide_id: str = Field(..., description="幻灯片ID")
    elements: List[ElementData] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="元素列表（1-50个）"
    )
    canvas_size: CanvasSize = Field(..., description="画布尺寸")
    options: Optional[OptimizationOptions] = Field(
        default=None,
        description="优化选项"
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="用户自定义提示词"
    )
    ai_model_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="AI模型配置（包含选择的模型名称等）"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="温度参数（0.0-2.0），控制生成多样性，None时使用模板默认值"
    )

    # 新增智能分析参数
    content_analysis: Optional[str] = Field(
        default=None,
        description="内容智能分析结果，用于指导布局选择和优化策略"
    )
    layout_type_hint: Optional[str] = Field(
        default=None,
        description="布局类型智能提示，基于内容语义分析的推荐布局类型"
    )


class LayoutOptimizationResponseData(BaseModel):
    """布局优化响应数据（data字段内容）"""
    slide_id: str = Field(..., description="幻灯片ID")
    elements: List[ElementData] = Field(..., description="优化后的元素列表")
    description: Optional[str] = Field(
        default=None,
        description="优化说明"
    )
    duration: Optional[float] = Field(
        default=None,
        description="优化耗时（秒）"
    )