"""
Celery队列管理相关的 Pydantic 模型
定义任务队列管理API的请求和响应数据结构
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class RevokeTaskRequest(BaseModel):
    """撤销任务请求"""
    terminate: bool = Field(default=False, description="是否强制终止")


# ==================== 响应模型 ====================

class ActiveTaskResponse(BaseModel):
    """活跃任务响应"""
    task_id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    worker: Optional[str] = Field(None, description="工作节点")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    eta: Optional[datetime] = Field(None, description="预计执行时间")


class QueueStatsResponse(BaseModel):
    """队列统计响应"""
    total_workers: int = Field(..., description="工作节点总数")
    active_tasks: int = Field(..., description="活跃任务数")
    scheduled_tasks: int = Field(..., description="已调度任务数")
    reserved_tasks: int = Field(..., description="已保留任务数")
    workers: List[Dict[str, Any]] = Field(default_factory=list, description="工作节点详情")
    timestamp: datetime = Field(..., description="统计时间戳")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态: healthy | unhealthy")
    message: str = Field(..., description="状态消息")
    workers: Optional[int] = Field(None, description="工作节点数量")
    active_tasks: Optional[int] = Field(None, description="活跃任务数")


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    total_cached: int = Field(..., description="已缓存URL总数")
    hit_count: int = Field(..., description="缓存命中次数")
    miss_count: int = Field(..., description="缓存未命中次数")
    hit_rate: float = Field(..., description="缓存命中率")
    last_refresh: Optional[datetime] = Field(None, description="最后刷新时间")
