"""
Banana PPT生成处理器
处理网络请求、日志记录和异常处理
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation.banana_generation_service import BananaGenerationService
from app.schemas.banana_generation import (
    SplitOutlineRequest,
    GenerateBatchSlidesRequest,
    RegenerateSlideRequest,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class BananaGenerationHandler:
    """Banana PPT生成处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = BananaGenerationService(db)

    async def handle_split_outline(
        self,
        request: SplitOutlineRequest
    ) -> Dict[str, Any]:
        """处理大纲拆分请求"""
        try:
            logger.info(
                "处理大纲拆分请求",
                extra={
                    "content_len": len(request.content),
                    "ai_model_id": request.ai_model_id
                }
            )

            result = await self.service.split_outline(
                content=request.content,
                ai_model_id=request.ai_model_id
            )

            logger.info(
                "大纲拆分完成",
                extra={
                    "slides_count": len(result.get("slides", [])),
                    "title": result.get("title", "")
                }
            )

            return result

        except Exception as e:
            logger.error(
                "大纲拆分失败",
                extra={
                    "ai_model_id": request.ai_model_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"大纲拆分失败: {str(e)}"
            )

    async def handle_generate_batch_slides(
        self,
        request: GenerateBatchSlidesRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理批量生成PPT请求"""
        try:
            # 验证template_id和custom_template_url至少有一个
            if not request.template_id and not request.custom_template_url:
                raise ValueError("template_id和custom_template_url必须提供其中一个")

            logger.info(
                "处理批量生成PPT请求",
                extra={
                    "template_id": request.template_id,
                    "has_custom_template": bool(request.custom_template_url),
                    "total_slides": len(request.outline.slides),
                    "generation_model": request.generation_model,
                    "user_id": user_id
                }
            )

            result = await self.service.generate_batch_slides(
                outline=request.outline.model_dump(),
                template_id=request.template_id,
                custom_template_url=request.custom_template_url,
                generation_model=request.generation_model,
                canvas_size=request.canvas_size.model_dump(),
                user_id=user_id
            )

            logger.info(
                "批量生成PPT任务已创建",
                extra={
                    "task_id": result.get("task_id"),
                    "total_slides": result.get("total_slides"),
                    "celery_task_id": result.get("celery_task_id")
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "批量生成PPT参数验证失败",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                "批量生成PPT失败",
                extra={
                    "template_id": request.template_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"批量生成PPT失败: {str(e)}"
            )

    async def handle_get_generation_status(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """处理查询生成状态请求"""
        try:
            status_data = await self.service.get_generation_status(task_id)

            logger.debug(
                "查询生成状态",
                extra={
                    "task_id": task_id,
                    "status": status_data.get("status"),
                    "completed": status_data.get("progress", {}).get("completed", 0),
                    "total": status_data.get("progress", {}).get("total", 0)
                }
            )

            return status_data

        except ValueError as e:
            logger.warning(
                "生成任务不存在",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                "查询生成状态失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询生成状态失败: {str(e)}"
            )

    async def handle_stop_generation(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """处理停止生成请求"""
        try:
            result = await self.service.stop_generation(task_id)

            logger.info(
                "停止生成任务",
                extra={
                    "task_id": task_id,
                    "completed_slides": result.get("completed_slides")
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "停止生成任务失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                "停止生成失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"停止生成失败: {str(e)}"
            )

    async def handle_regenerate_slide(
        self,
        request: RegenerateSlideRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理重新生成单张幻灯片请求"""
        try:
            logger.info(
                "处理重新生成幻灯片请求",
                extra={
                    "task_id": request.task_id,
                    "slide_index": request.slide_index,
                    "user_id": user_id
                }
            )

            result = await self.service.regenerate_slide(
                request.task_id,
                request.slide_index
            )

            logger.info(
                "重新生成幻灯片任务已创建",
                extra={
                    "task_id": request.task_id,
                    "slide_index": request.slide_index,
                    "celery_task_id": result.get("celery_task_id")
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "重新生成幻灯片参数验证失败",
                extra={
                    "task_id": request.task_id,
                    "slide_index": request.slide_index,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                "重新生成幻灯片失败",
                extra={
                    "task_id": request.task_id,
                    "slide_index": request.slide_index,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"重新生成幻灯片失败: {str(e)}"
            )

    async def handle_get_templates(
        self,
        template_type: Optional[str] = None,
        aspect_ratio: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理获取模板列表请求"""
        try:
            result = await self.service.get_templates(
                template_type=template_type,
                aspect_ratio=aspect_ratio
            )

            logger.info(
                "获取模板列表",
                extra={
                    "template_count": len(result.get("templates", [])),
                    "type": template_type,
                    "aspect_ratio": aspect_ratio
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取模板列表失败",
                extra={
                    "type": template_type,
                    "aspect_ratio": aspect_ratio,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取模板列表失败: {str(e)}"
            )
