"""
布局优化Handler（重处理）
负责网络层逻辑、日志记录、异常处理、缓存管理
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.layout.optimization.service import LayoutOptimizationService
from app.schemas.layout_optimization import (
    LayoutOptimizationRequest,
    LayoutOptimizationResponseData
)
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

logger = get_logger(__name__)


class LayoutOptimizationHandler:
    """布局优化处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = LayoutOptimizationService(db)

    def _generate_cache_key(self, request: LayoutOptimizationRequest) -> str:
        """生成缓存键（基于内容哈希）"""
        data = {
            "elements": [el.model_dump() for el in request.elements],
            "canvas_size": request.canvas_size.model_dump(),
            "options": request.options.model_dump() if request.options else {},
            "user_prompt": request.user_prompt or ""
        }

        content_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

        return f"layout_opt:{content_hash[:16]}"

    async def handle_optimize_layout(
        self,
        request: LayoutOptimizationRequest
    ) -> LayoutOptimizationResponseData:
        """
        处理布局优化请求

        Args:
            request: 布局优化请求

        Returns:
            LayoutOptimizationResponseData: 优化结果

        Raises:
            HTTPException: HTTP异常
        """
        start_time = time.time()

        try:
            # 记录开始日志（使用log_messages）
            logger.info(
                log_messages.START_OPERATION,
                operation_name="布局优化",
                slide_id=request.slide_id,
                elements_count=len(request.elements)
            )

            # TODO: 检查Redis缓存（第二阶段实现）
            # cache_key = self._generate_cache_key(request)
            # cached_result = await self._get_from_cache(cache_key)
            # if cached_result:
            #     logger.info(log_messages.OPERATION_SUCCESS,
            #                 operation_name="布局优化（缓存）",
            #                 cache_key=cache_key)
            #     return cached_result

            # 调用Service执行业务逻辑
            optimized_elements = await self.service.optimize_layout(
                slide_id=request.slide_id,
                elements=request.elements,
                canvas_size=request.canvas_size,
                options=request.options,
                user_prompt=request.user_prompt,
                ai_model_config=request.ai_model_config,
                temperature=request.temperature,
                content_analysis=request.content_analysis,
                layout_type_hint=request.layout_type_hint
            )

            # 构建响应数据
            duration = time.time() - start_time
            result = LayoutOptimizationResponseData(
                slide_id=request.slide_id,
                elements=optimized_elements,
                duration=duration
            )

            # TODO: 存储到Redis缓存（第二阶段实现）
            # await self._save_to_cache(cache_key, result)

            # 记录成功日志
            logger.info(
                log_messages.OPERATION_SUCCESS,
                operation_name="布局优化",
                slide_id=request.slide_id,
                duration_ms=int(duration * 1000),
                elements_count=len(optimized_elements)
            )

            return result

        except ValueError as e:
            # 业务验证异常
            logger.warning(
                "布局优化验证失败",
                operation="handle_optimize_layout",
                slide_id=request.slide_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e

        except Exception as e:
            # 其他异常
            duration = time.time() - start_time
            logger.error(
                log_messages.OPERATION_FAILED,
                operation_name="布局优化",
                slide_id=request.slide_id,
                duration_ms=int(duration * 1000),
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"布局优化失败：{str(e)}"
            ) from e