"""
标注处理器

职责:
- 处理网络层逻辑
- 日志记录和异常处理
- 调用服务层
- 数据转换和格式化
"""

from typing import Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.annotation.annotation_service import AnnotationService
from app.schemas.annotation import AnnotationStartRequest
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

logger = get_logger(__name__)


class AnnotationHandler:
    """标注处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.annotation_service = AnnotationService(db)

    async def handle_start_annotation(
        self,
        request: AnnotationStartRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        处理启动标注请求

        Args:
            request: 标注请求
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 任务信息
        """
        try:
            logger.info(
                "处理启动标注请求",
                extra={
                    "user_id": user_id,
                    "slide_count": len(request.slides),
                    "model_config": request.model_config.model_dump() if request.model_config else None
                }
            )

            # 验证请求
            self._validate_start_request(request)

            # 调用服务层启动标注
            result = await self.annotation_service.start_annotation(
                slides=request.slides,
                model_config=request.model_config,
                extraction_config=request.extraction_config,
                user_id=user_id
            )

            logger.info(
                "标注任务启动成功",
                extra={
                    "task_id": result["task_id"],
                    "estimated_time": result["estimated_time"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "标注请求验证失败",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="启动标注",
                exception=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"启动标注失败: {str(e)}"
            )

    async def handle_get_progress(self, task_id: str) -> Dict[str, Any]:
        """
        处理获取进度请求

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 进度信息
        """
        try:
            logger.info(
                "查询标注进度",
                extra={"task_id": task_id}
            )

            progress = await self.annotation_service.get_progress(task_id)

            return progress

        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="查询标注进度",
                extra={"task_id": task_id},
                exception=e
            )
            raise

    async def handle_get_results(self, task_id: str) -> Dict[str, Any]:
        """
        处理获取结果请求

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 标注结果
        """
        try:
            logger.info(
                "获取标注结果",
                extra={"task_id": task_id}
            )

            results = await self.annotation_service.get_results(task_id)

            logger.info(
                "标注结果获取成功",
                extra={
                    "task_id": task_id,
                    "result_count": len(results.get("results", []))
                }
            )

            return results

        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="获取标注结果",
                extra={"task_id": task_id},
                exception=e
            )
            raise

    async def handle_submit_corrections(
        self,
        task_id: str,
        corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理提交修正请求

        Args:
            task_id: 任务ID
            corrections: 修正数据

        Returns:
            Dict[str, Any]: 修正结果
        """
        try:
            logger.info(
                "提交用户修正",
                extra={
                    "task_id": task_id,
                    "correction_count": len(corrections)
                }
            )

            result = await self.annotation_service.submit_corrections(
                task_id,
                corrections
            )

            logger.info(
                "用户修正已应用",
                extra={
                    "task_id": task_id,
                    "applied_count": result.get("applied_corrections", 0)
                }
            )

            return result

        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="提交用户修正",
                extra={"task_id": task_id},
                exception=e
            )
            raise

    def _validate_start_request(self, request: AnnotationStartRequest):
        """验证启动请求"""
        if not request.slides or len(request.slides) == 0:
            raise ValueError("幻灯片数据不能为空")

        if len(request.slides) > 50:
            raise ValueError("单次标注最多支持50页幻灯片")

        # 验证每个幻灯片数据
        for slide in request.slides:
            if not slide.get("slide_id"):
                raise ValueError("幻灯片ID不能为空")
            # 允许没有截图的情况，但需要元素数据
            if not slide.get("elements"):
                raise ValueError(f"幻灯片 {slide['slide_id']} 缺少元素数据")