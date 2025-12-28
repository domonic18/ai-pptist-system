"""
标注处理器

职责:
- 处理网络层逻辑
- 日志记录和异常处理
- 调用服务层
- 数据转换和格式化
"""

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.annotation.annotation_service import AnnotationService
from app.services.annotation.single_annotation_service import SingleAnnotationService
from app.schemas.annotation import (
    SingleAnnotationRequest,
    BatchAnnotationRequest
)
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

logger = get_logger(__name__)


class AnnotationHandler:
    """标注处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.annotation_service = AnnotationService(db)

    async def handle_annotate_single_slide(
        self,
        request: SingleAnnotationRequest
    ) -> Dict[str, Any]:
        """
        处理单张幻灯片同步标注请求

        Args:
            request: 单张幻灯片标注请求

        Returns:
            Dict[str, Any]: 标注结果

        Raises:
            HTTPException: 处理失败时抛出异常
        """
        try:
            logger.info(
                "处理单张幻灯片标注请求",
                extra={"slide_id": request.slide.get("slide_id")}
            )

            # 验证请求
            self._validate_single_annotation_request(request)

            # 准备模型配置
            model_config = {
                "model_id": request.model_id,
                "multimodal_enabled": True
            }

            # 调用单页标注服务
            single_service = SingleAnnotationService(self.annotation_service)
            annotation = await single_service.annotate_single_slide(
                slide_data=request.slide,
                model_config=model_config
            )

            logger.info(
                "单张幻灯片标注完成",
                extra={"slide_id": request.slide.get("slide_id")}
            )

            return annotation

        except ValueError as e:
            logger.warning(
                "单张幻灯片标注请求验证失败",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="单张幻灯片标注",
                exception=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"标注失败: {str(e)}"
            ) from e

    async def handle_batch_annotation_start(
        self,
        request: BatchAnnotationRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        处理批量幻灯片标注请求

        Args:
            request: 批量标注请求
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 任务信息

        Raises:
            HTTPException: 处理失败时抛出异常
        """
        try:
            logger.info(
                "处理批量标注请求",
                extra={
                    "user_id": user_id,
                    "slide_count": len(request.slides),
                    "model_id": request.model_id
                }
            )

            # 验证请求
            self._validate_batch_annotation_request(request)

            # 调用服务层启动标注
            result = await self.annotation_service.start_annotation(
                slides=request.slides,
                model_config={
                    "model_id": request.model_id,
                    "multimodal_enabled": True
                },
                extraction_config={
                    "screenshot_quality": "high",
                    "include_element_data": True
                },
                user_id=user_id
            )

            logger.info(
                "批量标注任务启动成功",
                extra={
                    "task_id": result["task_id"],
                    "total_pages": result["total_pages"]
                }
            )

            return result

        except ValueError as e:
            logger.warning(
                "批量标注请求验证失败",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        except Exception as e:
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="批量标注启动",
                exception=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"启动批量标注失败: {str(e)}"
            ) from e

    def _validate_single_annotation_request(self, request: SingleAnnotationRequest):
        """验证单张幻灯片标注请求"""
        if not request.slide:
            raise ValueError("幻灯片数据不能为空")

        if not request.slide.get("slide_id"):
            raise ValueError("幻灯片ID不能为空")

        # 验证 model_id - 允许空字符串，后端会自动选择模型
        # model_id 是可选的，如果为空，后端会自动选择可用的视觉模型
        if request.model_id is None:
            raise ValueError("模型ID不能为空")
        # 注意：这里允许空字符串，因为前端可能发送空字符串让后端自动选择模型

    def _validate_batch_annotation_request(self, request: BatchAnnotationRequest):
        """验证批量标注请求"""
        if not request.slides or len(request.slides) == 0:
            raise ValueError("幻灯片列表不能为空")

        if len(request.slides) > 100:
            raise ValueError("批量标注最多支持100页幻灯片")

        # 验证每个幻灯片数据
        for slide in request.slides:
            if not slide.get("slide_id"):
                raise ValueError("幻灯片ID不能为空")

        # 验证 model_id - 允许空字符串，后端会自动选择模型
        # model_id 是可选的，如果为空，后端会自动选择可用的视觉模型
        if request.model_id is None:
            raise ValueError("模型ID不能为空")
        # 注意：这里允许空字符串，因为前端可能发送空字符串让后端自动选择模型
