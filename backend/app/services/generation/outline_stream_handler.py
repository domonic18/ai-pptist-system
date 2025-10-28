"""
大纲流式生成处理器
处理大纲流式生成相关的业务逻辑，提供统一的错误处理和日志记录
"""

from typing import AsyncGenerator
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation.outline_stream_service import OutlineStreamService
from app.core.log_utils import get_logger
from app.schemas.generation_outline import OutlineGenerationRequest

logger = get_logger(__name__)


class OutlineStreamHandler:
    """大纲流式生成处理器"""

    def __init__(self, db: AsyncSession):
        """
        初始化处理器

        Args:
            db: 数据库会话
        """
        self.db = db
        self.stream_service = OutlineStreamService()

    async def handle_outline_stream_generation(
        self,
        request: OutlineGenerationRequest,
        req: Request = None
    ) -> AsyncGenerator[str, None]:
        """
        处理流式生成大纲请求

        Args:
            request: 大纲生成请求
            req: FastAPI请求对象

        Returns:
            AsyncGenerator[str, None]: SSE事件生成器
        """
        import time
        start_time = time.time()

        logger.info(
            "开始流式生成演示文稿大纲",
            operation="outline_stream_generation_start",
            title=request.title[:50] if request.title else "Untitled",
            slide_count=request.slide_count,
            language=request.language,
            input_content_length=len(request.input_content) if request.input_content else 0
        )

        try:
            # 流式生成大纲内容
            async for event in self.stream_service.generate_outline_stream(
                title=request.title,
                input_content=request.input_content,
                slide_count=request.slide_count or 8,
                language=request.language or "zh-CN",
                model_config=request.model_settings
            ):
                yield f"data: {event}\n\n"

            # 记录成功日志
            generation_time = time.time() - start_time
            logger.info(
                "演示文稿大纲流式生成成功",
                operation="outline_stream_generation_success",
                title=request.title[:50] if request.title else "Untitled",
                generation_time=generation_time,
                language=request.language
            )

        except HTTPException as http_exc:
            # 对于HTTP异常，发送错误事件但不重新抛出
            logger.error(
                "流式生成演示文稿大纲失败 - HTTP异常",
                operation="outline_stream_generation_http_failed",
                exception=http_exc,
                title=request.title[:50] if request.title else "Untitled",
                slide_count=request.slide_count
            )

            error_event = {
                "event": "error",
                "data": {
                    "error": f"HTTP错误: {str(http_exc.detail)}",
                    "code": "HTTP_ERROR",
                    "timestamp": time.time()
                }
            }
            import json
            error_event_json = json.dumps(error_event, ensure_ascii=False)
            yield f"data: {error_event_json}\n\n"
        except Exception as e:
            # 记录错误日志
            logger.error(
                "流式生成演示文稿大纲失败",
                operation="outline_stream_generation_failed",
                exception=e,
                title=request.title[:50] if request.title else "Untitled",
                slide_count=request.slide_count
            )

            # 发送错误事件，但不重新抛出异常
            error_event = {
                "event": "error",
                "data": {
                    "error": f"生成失败: {str(e)}",
                    "code": "OUTLINE_GENERATION_ERROR",
                    "timestamp": time.time()
                }
            }
            import json
            error_event_json = json.dumps(error_event, ensure_ascii=False)
            yield f"data: {error_event_json}\n\n"