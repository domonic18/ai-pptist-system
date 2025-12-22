from celery import group
from app.services.tasks.celery_app import celery_app
from app.core.log_utils import get_logger
from app.core.config import settings
from app.models.banana_generation_task import TaskStatus

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
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
):
    """生成单张幻灯片图片的Celery任务"""
    logger.info("开始生成幻灯片", extra={
        "task_id": task_id,
        "slide_index": slide_index,
        "celery_task_id": self.request.id
    })

    try:
        import asyncio
        from app.db.redis import get_redis
        from app.services.generation.banana_slide_generator import BananaSlideGenerator

        # 初始化和Redis
        redis_client = get_redis()
        generator = BananaSlideGenerator()

        # 构建生成配置
        generation_config = {
            'ppt_title': slide_data.get('ppt_title', 'PPT演示'),
            'total_pages': slide_data.get('total_pages', len(slide_data.get('slides', [])))
        }
        slide_data.update(generation_config)

        # 生成图片
        result = asyncio.run(
            generator.generate_single_slide(
                slide_index=slide_index,
                slide_data=slide_data,
                template_image_url=template_image_url,
                generation_model=generation_model,
                canvas_size=canvas_size
            )
        )

        if not result or 'pil_image' not in result:
            raise Exception("生成结果未包含PIL图像")

        # 上传到腾讯云COS
        cos_url = asyncio.run(
            generator.upload_image_to_cos(
                task_id=task_id,
                slide_index=slide_index,
                image=result['pil_image']
            )
        )

        # 更新Redis状态
        asyncio.run(
            generator.update_slide_result_in_redis(
                redis_client=redis_client,
                task_id=task_id,
                slide_index=slide_index,
                generation_result=result,
                cos_url=cos_url
            )
        )

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

    except Exception as exc:
        logger.error("幻灯片生成失败", extra={
            "task_id": task_id,
            "slide_index": slide_index,
            "error": str(exc),
            "retry_count": self.request.retries
        })

        if self.request.retries < self.max_retries:
            countdown = 5 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        else:
            try:
                import asyncio
                from app.db.redis import get_redis
                from app.services.generation.banana_task_manager import BananaTaskManager

                redis_client = get_redis()
                task_manager = BananaTaskManager(redis_client)

                asyncio.run(
                    task_manager.update_slide_status(
                        task_id=task_id,
                        slide_index=slide_index,
                        status="failed",
                        error=str(exc),
                        retry_count=self.request.retries
                    )
                )
            except Exception as update_exc:
                logger.error("标记失败状态失败", extra={
                    "task_id": task_id,
                    "slide_index": slide_index,
                    "update_error": str(update_exc)
                })

            return {
                "slide_index": slide_index,
                "status": "failed",
                "error": str(exc)
            }


@celery_app.task(queue='banana')
def generate_batch_slides_task(
    task_id: str,
    slides: list,
    template_image_url: str,
    generation_model: str,
    canvas_size: dict
):
    """批量生成幻灯片图片的协调任务"""
    logger.info("开始批量生成任务", extra={
        "task_id": task_id,
        "total_slides": len(slides)
    })

    try:
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

        result = job.apply_async()

        from app.db.database import get_db
        from app.repositories.banana_generation import BananaGenerationRepository

        db = next(get_db())
        repo = BananaGenerationRepository(db)
        repo.update_task_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            celery_group_id=result.id
        )

        logger.info("批量任务已提交", extra={
            "task_id": task_id,
            "celery_group_id": result.id,
            "total_slides": len(slides)
        })

        return {
            "task_id": task_id,
            "celery_group_id": result.id,
            "total_slides": len(slides),
            "status": "submitted"
        }

    except Exception as e:
        logger.error("批量任务提交失败", extra={
            "task_id": task_id,
            "error": str(e)
        })
        raise
