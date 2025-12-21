"""
幻灯片流式生成处理器
处理幻灯片流式生成相关的业务逻辑，提供统一的错误处理和日志记录
"""

from typing import AsyncGenerator
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation.slides_stream_service import SlidesStreamService
from app.core.log_utils import get_logger
from app.schemas.generation_slides import SlidesGenerationRequest
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)




class SlidesStreamHandler:
    """幻灯片流式生成处理器"""

    def __init__(self, db: AsyncSession):
        """
        初始化处理器

        Args:
            db: 数据库会话
        """
        self.db = db
        self.stream_service = SlidesStreamService()

    async def handle_slides_stream_generation(
        self,
        request: SlidesGenerationRequest,
        req: Request = None
    ) -> AsyncGenerator[str, None]:
        """
        处理流式生成幻灯片请求

        Args:
            request: 幻灯片生成请求
            req: FastAPI请求对象

        Returns:
            AsyncGenerator[str, None]: SSE事件生成器
        """
        import time
        start_time = time.time()

        logger.info(
            "开始流式生成演示文稿幻灯片",
            operation="slides_stream_generation_start",
            content_length=len(request.content),
            language=request.language,
            style=request.style
        )

        try:
            # 准备AI模型配置
            ai_model_config = None
            if request.model:
                # 从数据库获取完整的模型配置
                ai_model_repo = AIModelRepository(self.db)
                ai_model = await ai_model_repo.get_model_by_id(request.model)

                if not ai_model:
                    raise ValueError(f"未找到模型: {request.model}")

                if not ai_model.is_enabled:
                    raise ValueError(f"模型已禁用: {ai_model.name}")

                # 构建完整的模型配置字典
                ai_model_config = {
                    'id': ai_model.id,
                    'ai_model_name': ai_model.ai_model_name,
                    'base_url': ai_model.base_url,
                    'api_key': ai_model.api_key,
                    'capabilities': ai_model.capabilities,
                    'provider_mapping': ai_model.provider_mapping,
                    'max_tokens': ai_model.max_tokens,
                    'context_window': ai_model.context_window,
                    'parameters': ai_model.parameters or {}
                }

                logger.info(
                    "使用模型配置生成幻灯片",
                    operation="slides_model_config_prepared",
                    model_id=ai_model.id,
                    model_name=ai_model.name,
                    has_api_key=bool(ai_model.api_key),
                    api_key_length=len(ai_model.api_key) if ai_model.api_key else 0
                )

            # 直接使用原始Markdown内容流式生成幻灯片内容
            async for event in self.stream_service.generate_slides_stream(
                content=request.content,
                language=request.language or "中文",
                style=request.style or "professional",
                ai_model_config=ai_model_config
            ):
                yield f"data: {event}\n\n"

            # 记录成功日志
            generation_time = time.time() - start_time
            logger.info(
                "演示文稿幻灯片流式生成成功",
                operation="slides_stream_generation_success",
                content_length=len(request.content),
                generation_time=generation_time,
                language=request.language
            )

        except HTTPException as http_exc:
            # 对于HTTP异常，发送错误事件但不重新抛出
            logger.error(
                "流式生成演示文稿幻灯片失败 - HTTP异常",
                operation="slides_stream_generation_http_failed",
                exception=http_exc,
                content_length=len(request.content)
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
                "流式生成演示文稿幻灯片失败",
                operation="slides_stream_generation_failed",
                exception=e,
                content_length=len(request.content)
            )

            # 发送错误事件，但不重新抛出异常
            error_event = {
                "event": "error",
                "data": {
                    "error": f"生成失败: {str(e)}",
                    "code": "SLIDES_GENERATION_ERROR",
                    "timestamp": time.time()
                }
            }
            import json
            error_event_json = json.dumps(error_event, ensure_ascii=False)
            yield f"data: {error_event_json}\n\n"