"""
Banana生成PPT API端点
提供批量生成PPT幻灯片图片的功能
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.generation.banana_generation_handler import BananaGenerationHandler
from app.schemas.banana_generation import (
    SplitOutlineRequest,
    GenerateBatchSlidesRequest,
    RegenerateSlideRequest,
)
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Banana生成"])


# 辅助函数：获取当前用户ID
def get_current_user_id():
    """获取当前用户ID（简化版本，实际应从token获取）"""
    # TODO: 实际项目中应实现用户认证
    return "demo_001"


@router.post(
    "/split_outline",
    response_model=StandardResponse,
    summary="拆分大纲",
    description="将Markdown大纲拆分为结构化的幻灯片数据"
)
async def split_outline(
    request: SplitOutlineRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    将Markdown大纲拆分为结构化的幻灯片数据

    Args:
        request: 包含原始大纲内容和模型ID的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 结构化的幻灯片数据 {title, slides: [{title, points}]}
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_split_outline(request)

    return StandardResponse(
        status="success",
        message="大纲拆分成功",
        data=data
    )


@router.post(
    "/generate_batch_slides",
    response_model=StandardResponse,
    summary="批量生成PPT",
    description="批量生成PPT幻灯片图片，返回任务ID供轮询"
)
async def generate_batch_slides(
    request: GenerateBatchSlidesRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    批量生成PPT幻灯片图片

    流程：
    1. 接收PPT大纲和模板信息
    2. 创建生成任务记录
    3. 提交Celery任务到队列
    4. 立即返回task_id，前端轮询获取结果

    Args:
        request: 包含大纲、模板ID、生成模型等信息的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含task_id、total_slides、status的任务信息
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_generate_batch_slides(request, user_id)

    return StandardResponse(
        status="success",
        message=f"PPT生成任务已创建，共{data.get('total_slides')}张幻灯片",
        data=data
    )


@router.get(
    "/generation_status/{task_id}",
    response_model=StandardResponse,
    summary="查询生成状态",
    description="查询生成任务状态（前端轮询端点）"
)
async def get_generation_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    查询生成任务状态（前端轮询端点）

    核心机制：前端每2秒查询一次，获取最新进度和已完成的图片URL
    Redis状态由Celery Worker在生成完成后更新

    Args:
        task_id: 生成任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 包含任务状态、进度、每页详细状态（含COS图片URL）
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_get_generation_status(task_id)

    return StandardResponse(
        status="success",
        message="查询成功",
        data=data
    )


@router.post(
    "/stop_generation/{task_id}",
    response_model=StandardResponse,
    summary="停止生成",
    description="停止正在进行的生成任务"
)
async def stop_generation(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    停止生成任务

    取消正在进行的Celery任务，并更新任务状态

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        StandardResponse: 停止结果
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_stop_generation(task_id)

    return StandardResponse(
        status="success",
        message=f"任务已停止，已完成{data.get('completed_slides')}/{data.get('total_slides')}张",
        data=data
    )


@router.post(
    "/regenerate_slide",
    response_model=StandardResponse,
    summary="重新生成单张幻灯片",
    description="重新生成失败的幻灯片或不满意的结果"
)
async def regenerate_slide(
    request: RegenerateSlideRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
) -> StandardResponse:
    """
    重新生成单张幻灯片

    用于替换生成失败的页面或重新生成不满意的结果

    Args:
        request: 包含task_id和slide_index的请求
        db: 数据库会话
        user_id: 当前用户ID

    Returns:
        StandardResponse: 包含slide_index、status、celery_task_id的结果
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_regenerate_slide(request, user_id)

    return StandardResponse(
        status="success",
        message=f"第{request.slide_index + 1}张幻灯片重新生成任务已创建",
        data=data
    )


@router.get(
    "/templates",
    response_model=StandardResponse,
    summary="获取模板列表",
    description="获取可用的PPT模板列表"
)
async def get_templates(
    type: str = Query(None, description="模板类型: system|user"),
    aspect_ratio: str = Query(None, description="宽高比: 16:9|4:3"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取可用模板列表

    返回系统中可用的PPT模板，包括系统预设和用户上传的

    Args:
        type: 模板类型过滤（可选）
        aspect_ratio: 宽高比过滤（可选）
        db: 数据库会话

    Returns:
        StandardResponse: 包含templates数组
    """
    handler = BananaGenerationHandler(db)
    data = await handler.handle_get_templates(type, aspect_ratio)

    return StandardResponse(
        status="success",
        message=f"获取到{len(data.get('templates', []))}个模板",
        data=data
    )
