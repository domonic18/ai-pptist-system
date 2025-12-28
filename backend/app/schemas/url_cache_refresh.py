"""
URL缓存刷新相关的 Pydantic 模型
定义URL刷新API的请求和响应数据结构
"""

from typing import List
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class UrlRefreshRequest(BaseModel):
    """URL刷新请求"""
    image_key: str = Field(..., description="图片键")
    force_refresh: bool = Field(default=False, description="是否强制刷新")


class BatchUrlRefreshRequest(BaseModel):
    """批量URL刷新请求"""
    image_keys: List[str] = Field(..., description="图片键列表")
    batch_size: int = Field(default=50, ge=1, le=100, description="每批处理数量")


class ScheduleRefreshRequest(BaseModel):
    """定期刷新请求"""
    image_key: str = Field(..., description="图片键")
    refresh_interval: int = Field(default=3600, ge=60, description="刷新间隔（秒）")


# ==================== 响应模型 ====================

class UrlRefreshResponse(BaseModel):
    """URL刷新响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")
