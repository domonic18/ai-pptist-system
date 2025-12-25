"""
Banana PPT 生成 Celery 任务

负责将图片生成任务异步化执行，支持：
- 单张幻灯片生成
- 批量幻灯片生成（并行处理）
"""

from typing import Dict, Any
from celery import group

from app.services.tasks.celery_app import celery_app
from app.core.log_utils import get_logger
from app.models.banana_generation_task import TaskStatus
from app.utils.async_utils import AsyncRunner

logger = get_logger(__name__)


# ============================================================================
# 单张幻灯片生成任务
# ============================================================================

@celery_app.task(
    bind=True,
    time_limit=600,
    soft_time_limit=540,
    queue='banana'
)
def generate_single_slide_task(
    self,
    task_id: str,
    slide_index: int,
    slide_data: dict,
    template_image_url: str,
    generation_model: str,
    canvas_size: dict
) -> Dict[str, Any]:
    """
    生成单张幻灯片图片的 Celery 任务
    
    Args:
        task_id: 任务ID
        slide_index: 幻灯片索引
        slide_data: 幻灯片数据（包含 title, points, ppt_title, total_pages）
        template_image_url: 模板图片URL
        generation_model: 生成模型ID
        canvas_size: 画布尺寸 {width, height}
        
    Returns:
        生成结果字典
    """
    logger.info("开始生成幻灯片", extra={
        "task_id": task_id,
        "slide_index": slide_index,
        "celery_task_id": self.request.id
    })

    try:
        return _execute_slide_generation(
            task_id=task_id,
            slide_index=slide_index,
            slide_data=slide_data,
            template_image_url=template_image_url,
            generation_model=generation_model,
            canvas_size=canvas_size
        )
    except Exception as exc:
        return _handle_generation_error(
            self=self,
            task_id=task_id,
            slide_index=slide_index,
            error=exc
        )


def _execute_slide_generation(
    task_id: str,
    slide_index: int,
    slide_data: dict,
    template_image_url: str,
    generation_model: str,
    canvas_size: dict
) -> Dict[str, Any]:
    """
    执行单张幻灯片生成的核心逻辑
    
    将异步操作封装在 AsyncRunner 中统一管理
    """
    from app.core.cache.redis import get_redis
    from app.db.database import AsyncSessionLocal
    from app.services.generation.banana_slide_generator import BananaSlideGenerator

    with AsyncRunner() as runner:
        async def do_generation():
            # 1. 初始化 Redis (get_redis 现在会处理 loop 变更)
            redis_client = await get_redis()

            # 2. 使用数据库会话生成图片
            async with AsyncSessionLocal() as db:
                generator = BananaSlideGenerator(db=db)
                try:
                    # A. 生成图片
                    result = await generator.generate_single_slide(
                        slide_index=slide_index,
                        slide_data=slide_data,
                        template_image_url=template_image_url,
                        generation_model=generation_model,
                        canvas_size=canvas_size
                    )

                    if not result or 'pil_image' not in result:
                        raise ValueError("生成结果未包含PIL图像")

                    # B. 上传到腾讯云COS
                    cos_url = await generator.upload_image_to_cos(
                        task_id=task_id,
                        slide_index=slide_index,
                        image=result['pil_image']
                    )

                    # C. 更新Redis状态
                    await generator.update_slide_result_in_redis(
                        redis_client=redis_client,
                        task_id=task_id,
                        slide_index=slide_index,
                        generation_result=result,
                        cos_url=cos_url
                    )
                    
                    return cos_url, result
                finally:
                    # 显式关闭 generator 以释放 AI Provider 资源（如 httpx 客户端）
                    # 避免 "Event loop is closed" 错误
                    await generator.close()
        
        cos_url, result = runner.run(do_generation())

        logger.info("幻灯片生成成功", extra={
            "task_id": task_id,
            "slide_index": slide_index,
            "cos_url": cos_url
        })

        return {
            "slide_index": slide_index,
            "status": "completed",
            "cos_url": cos_url,
            "generation_time": result.get("generation_time")
        }


def _handle_generation_error(
    self,
    task_id: str,
    slide_index: int,
    error: Exception
) -> Dict[str, Any]:
    """
    处理生成失败的情况

    标记任务为失败状态，不进行重试
    """
    logger.error("幻灯片生成失败", extra={
        "task_id": task_id,
        "slide_index": slide_index,
        "error": str(error)
    })

    # 标记失败
    _mark_slide_as_failed(task_id, slide_index, error)

    return {
        "slide_index": slide_index,
        "status": "failed",
        "error": str(error)
    }


def _mark_slide_as_failed(task_id: str, slide_index: int, error: Exception):
    """在 Redis 中标记幻灯片生成失败"""
    try:
        from app.core.cache.redis import get_redis
        from app.services.generation.banana_task_manager import BananaTaskManager
        from app.utils.async_utils import run_async

        async def update_failed_status():
            redis_client = await get_redis()
            task_manager = BananaTaskManager(redis_client)
            await task_manager.update_slide_status(
                task_id=task_id,
                slide_index=slide_index,
                status="failed",
                error=str(error)
            )
        
        run_async(update_failed_status())
        
    except Exception as update_exc:
        logger.error("标记失败状态失败", extra={
            "task_id": task_id,
            "slide_index": slide_index,
            "update_error": str(update_exc)
        })


# ============================================================================
# 批量幻灯片生成任务
# ============================================================================

@celery_app.task(queue='banana')
def generate_batch_slides_task(
    task_id: str,
    slides: list,
    template_image_url: str,
    generation_model: str,
    canvas_size: dict
) -> Dict[str, Any]:
    """
    批量生成幻灯片图片的协调任务
    
    创建一组并行任务来生成所有幻灯片
    
    Args:
        task_id: 任务ID
        slides: 幻灯片数据列表
        template_image_url: 模板图片URL
        generation_model: 生成模型ID
        canvas_size: 画布尺寸
        
    Returns:
        任务提交结果
    """
    logger.info("开始批量生成任务", extra={
        "task_id": task_id,
        "total_slides": len(slides)
    })

    try:
        # 1. 创建并行任务组
        job = group(
            generate_single_slide_task.s(
                task_id=task_id,
                slide_index=i,
                slide_data=slide,
                template_image_url=template_image_url,
                generation_model=generation_model,
                canvas_size=canvas_size
            )
            for i, slide in enumerate(slides)
        )

        # 2. 提交任务组到 banana 队列
        group_result = job.apply_async(queue='banana')
        
        # 3. 更新数据库中的任务状态
        _update_task_with_group_id(task_id, group_result.id)

        logger.info("批量任务已提交", extra={
            "task_id": task_id,
            "celery_group_id": group_result.id,
            "total_slides": len(slides)
        })

        return {
            "task_id": task_id,
            "celery_group_id": group_result.id,
            "total_slides": len(slides),
            "status": "submitted"
        }

    except Exception as e:
        logger.error("批量任务提交失败", extra={
            "task_id": task_id,
            "error": str(e)
        })
        raise


def _update_task_with_group_id(task_id: str, group_id: str):
    """更新数据库中的任务状态，记录 Celery 任务组 ID"""
    from app.db.database import AsyncSessionLocal
    from app.repositories.banana_generation import BananaGenerationRepository
    from app.utils.async_utils import run_async
    
    async def do_update():
        async with AsyncSessionLocal() as db:
            repo = BananaGenerationRepository(db)
            await repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                celery_group_id=group_id
            )
            await db.commit()
    
    run_async(do_update())
