"""
图片编辑处理器
处理网络请求、日志记录和异常处理
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.repositories.image_editing import ImageEditingRepository
from app.services.editing.image_editing_service import ImageEditingService
from app.schemas.image_editing import (
    ParseAndRemoveRequest,
    HybridOCRParseRequest,
    MinerUParseRequest,
)
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageEditingHandler:
    """图片编辑处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = ImageEditingService(db)
        self.repo = ImageEditingRepository(db)

    async def handle_parse_with_mineru(
        self,
        request: MinerUParseRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理MinerU识别请求"""
        try:
            logger.info(
                "处理MinerU识别请求",
                extra={
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key,
                    "enable_formula": request.enable_formula,
                    "enable_table": request.enable_table,
                    "enable_style_recognition": request.enable_style_recognition
                }
            )

            # 生成任务ID
            task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # 创建任务记录
            await self.repo.create_task(
                task_id=task_id,
                slide_id=request.slide_id,
                original_cos_key=request.cos_key,
                user_id=user_id
            )

            # 提交到Celery队列
            from app.services.tasks.image_editing_tasks import mineru_task
            celery_task = mineru_task.apply_async(
                kwargs={
                    "task_id": task_id,
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key,
                    "user_id": user_id,
                    "enable_formula": request.enable_formula,
                    "enable_table": request.enable_table,
                    "enable_style_recognition": request.enable_style_recognition,
                    "remove_text": request.remove_text
                },
                queue="image_editing"
            )

            logger.info(
                "MinerU任务已提交到Celery队列",
                extra={
                    "task_id": task_id,
                    "celery_task_id": celery_task.id,
                    "slide_id": request.slide_id
                }
            )

            # 估算时间
            estimated_time = 10
            if request.remove_text:
                estimated_time += 15

            return {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": estimated_time,
                "message": "MinerU识别任务已创建，正在处理中"
            }

        except Exception as e:
            logger.error(
                "MinerU任务创建失败",
                extra={
                    "slide_id": request.slide_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinerU任务创建失败: {str(e)}"
            ) from e

    async def handle_parse_with_hybrid_ocr(
        self,
        request: HybridOCRParseRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理混合OCR识别请求"""
        try:
            logger.info(
                "处理混合OCR识别请求",
                extra={
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key
                }
            )

            # 生成任务ID
            task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # 创建任务记录
            await self.repo.create_task(
                task_id=task_id,
                slide_id=request.slide_id,
                original_cos_key=request.cos_key,
                user_id=user_id
            )

            # 提交到Celery队列
            from app.services.tasks.image_editing_tasks import hybrid_ocr_task
            celery_task = hybrid_ocr_task.apply_async(
                kwargs={
                    "task_id": task_id,
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key,
                    "user_id": user_id
                },
                queue="image_editing"
            )

            logger.info(
                "混合OCR任务已提交到Celery队列",
                extra={
                    "task_id": task_id,
                    "celery_task_id": celery_task.id,
                    "slide_id": request.slide_id
                }
            )

            return {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 8,
                "message": "OCR识别任务已创建，正在处理中"
            }

        except Exception as e:
            logger.error(
                "混合OCR任务创建失败",
                extra={
                    "slide_id": request.slide_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"混合OCR任务创建失败: {str(e)}"
            ) from e

    async def handle_get_editing_status(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """处理查询编辑状态请求"""
        try:
            result = await self.service.get_editing_result(task_id)

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="任务不存在"
                )

            logger.debug(
                "查询编辑状态",
                extra={
                    "task_id": task_id,
                    "status": result["status"],
                    "progress": result["progress"]
                }
            )

            # 构建响应数据
            response_data = {
                "task_id": result["task_id"],
                "slide_id": result["slide_id"],
                "status": result["status"],
                "progress": result["progress"]
            }

            # 添加当前步骤
            if result.get("current_step"):
                response_data["current_step"] = result["current_step"]

            # 如果已完成，包含完整结果
            if result["status"] == "completed":
                if result.get("ocr_result"):
                    response_data["ocr_result"] = result["ocr_result"]
                if result.get("edited_image"):
                    response_data["edited_image"] = result["edited_image"]

            # 如果失败，包含错误信息
            if result.get("error_message"):
                response_data["error_message"] = result["error_message"]

            return response_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "查询编辑状态失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询编辑状态失败: {str(e)}"
            ) from e

    async def handle_parse_and_remove_text(
        self,
        request: ParseAndRemoveRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理一步完成：OCR识别 + 文字去除请求"""
        try:
            # 获取OCR引擎，默认使用配置的默认引擎
            ocr_engine = request.ocr_engine or "hybrid_ocr"

            logger.info(
                "处理图片编辑请求（一步完成）",
                extra={
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key,
                    "ai_model_id": request.ai_model_id,
                    "ocr_engine": ocr_engine
                }
            )

            # 生成任务ID
            task_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # 创建任务记录
            await self.repo.create_task(
                task_id=task_id,
                slide_id=request.slide_id,
                original_cos_key=request.cos_key,
                user_id=user_id
            )

            # 根据OCR引擎选择提交不同的任务
            if ocr_engine == "mineru":
                # 使用MinerU任务
                from app.services.tasks.image_editing_tasks import mineru_task
                celery_task = mineru_task.apply_async(
                    kwargs={
                        "task_id": task_id,
                        "slide_id": request.slide_id,
                        "cos_key": request.cos_key,
                        "user_id": user_id,
                        "enable_formula": True,
                        "enable_table": True,
                        "enable_style_recognition": True,
                        "remove_text": True
                    },
                    queue="image_editing"
                )
                estimated_time = 25
                message = "MinerU识别+文字去除任务已创建，正在处理中"
            else:
                # 使用混合OCR任务（默认）
                from app.services.tasks.image_editing_tasks import full_editing_task
                celery_task = full_editing_task.apply_async(
                    kwargs={
                        "task_id": task_id,
                        "slide_id": request.slide_id,
                        "cos_key": request.cos_key,
                        "user_id": user_id,
                        "ai_model_id": request.ai_model_id
                    },
                    queue="image_editing"
                )
                estimated_time = 20
                message = "编辑任务已创建，正在处理中"

            logger.info(
                "图片编辑任务已提交到Celery队列",
                extra={
                    "task_id": task_id,
                    "celery_task_id": celery_task.id,
                    "slide_id": request.slide_id,
                    "ocr_engine": ocr_engine
                }
            )

            return {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": estimated_time,
                "message": message
            }

        except Exception as e:
            logger.error(
                "图片编辑任务创建失败",
                extra={
                    "slide_id": request.slide_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"图片编辑任务创建失败: {str(e)}"
            ) from e
