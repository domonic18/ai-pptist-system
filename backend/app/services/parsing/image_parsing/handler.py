"""
图片解析处理器
处理网络请求、日志记录和异常处理
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.repositories.image_parsing import ImageParsingRepository
from app.services.parsing.image_parsing.service import ImageParsingService
from app.schemas.image_parsing import ParseRequest
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageParsingHandler:
    """图片解析处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = ImageParsingService(db)
        self.repo = ImageParsingRepository(db)

    async def handle_parse_image(
        self,
        request: ParseRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """处理图片解析请求"""
        try:
            logger.info(
                "处理图片解析请求",
                extra={
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key
                }
            )

            # 生成任务ID
            task_id = f"parse_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # 创建任务记录
            await self.repo.create_task(
                task_id=task_id,
                slide_id=request.slide_id,
                cos_key=request.cos_key,
                user_id=user_id
            )

            # 提交到Celery队列
            from app.services.tasks.image_parsing_tasks import parse_image_task
            celery_task = parse_image_task.apply_async(
                kwargs={
                    "task_id": task_id,
                    "slide_id": request.slide_id,
                    "cos_key": request.cos_key,
                    "user_id": user_id
                },
                queue="image_parsing"
            )

            logger.info(
                "图片解析任务已提交到Celery队列",
                extra={
                    "task_id": task_id,
                    "celery_task_id": celery_task.id,
                    "slide_id": request.slide_id
                }
            )

            return {
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 5,
                "message": "解析任务已创建，正在处理中"
            }

        except Exception as e:
            logger.error(
                "图片解析任务创建失败",
                extra={
                    "slide_id": request.slide_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"图片解析任务创建失败: {str(e)}"
            ) from e

    async def handle_get_parse_status(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """处理查询解析状态请求"""
        try:
            result = await self.service.get_parse_result(task_id)

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="任务不存在"
                )

            logger.debug(
                "查询解析状态",
                extra={
                    "task_id": task_id,
                    "status": result.status,
                    "progress": result.progress
                }
            )

            # 构建响应数据
            response_data = {
                "task_id": result.task_id,
                "slide_id": result.slide_id,
                "cos_key": result.cos_key,
                "status": result.status,
                "progress": result.progress
            }

            # 如果已完成，包含完整结果
            if result.status == "completed":
                response_data["text_regions"] = [
                    region.model_dump() for region in result.text_regions
                ]
                if result.metadata:
                    response_data["metadata"] = result.metadata.model_dump()
                else:
                    logger.warning(
                        "任务已完成但metadata为空",
                        extra={"task_id": task_id}
                    )

            return response_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "查询解析状态失败",
                extra={"task_id": task_id, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询解析状态失败: {str(e)}"
            ) from e
