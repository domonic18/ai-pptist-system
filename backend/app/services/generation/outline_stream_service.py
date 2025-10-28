"""
大纲流式生成服务
负责流式生成演示文稿大纲
支持Mock模式用于开发和调试环境
"""

import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
from app.core.log_utils import get_logger
from app.core.config import settings
from app.prompts import get_prompt_manager
from app.services.generation.stream.outline_helper import OutlineHelper
from app.core.llm.client import AIClient
from app.services.generation.stream.common_utils import StreamEventGenerator
from app.prompts import PromptHelper
from app.services.generation.stream.mock_outline import mock_outline_service

logger = get_logger(__name__)


class OutlineStreamService:
    """大纲流式生成服务"""

    def __init__(self):
        """初始化大纲流式生成服务"""
        self.prompt_manager = get_prompt_manager()
        self.helper = OutlineHelper()
        self.ai_service = AIClient()

        # 初始化通用工具
        self.stream_events = StreamEventGenerator()
        self.prompt_helper = PromptHelper(self.prompt_manager)

    async def generate_outline_stream(
        self,
        title: str,
        input_content: Optional[str] = None,
        slide_count: int = 8,
        language: str = "zh-CN",
        model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成演示文稿大纲

        Args:
            title: 演示文稿标题
            input_content: 输入内容或提示
            slide_count: 幻灯片数量
            language: 输出语言
            model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: SSE事件生成器
        """
        start_time = time.time()

        try:
            # 发送开始事件
            async for event in self.stream_events.send_start_event(
                "outline_generation",
                {
                    "title": title,
                    "slide_count": slide_count,
                    "language": language,
                    "mock_mode": settings.enable_outline_mock
                }
            ):
                yield event

            # 准备提示词和配置
            system_prompt, user_prompt, temperature, max_tokens = \
                self.prompt_helper.prepare_prompts(
                    "presentation",
                    "outline_generation",
                    {
                        "prompt": f"{title}\n\n{input_content or ''}",
                        "slide_count": slide_count,
                        "language": language
                    },
                    {
                        "slide_count": slide_count,
                        "language": language
                    }
                )

            # 发送提示词准备完成事件
            async for event in self.stream_events.send_prompt_ready_event(
                system_prompt, user_prompt, temperature, max_tokens
            ):
                yield event

            # 根据配置选择使用AI服务还是Mock服务
            if settings.enable_outline_mock:
                logger.info(
                    "使用Mock模式生成大纲",
                    operation="outline_generation_mock_mode",
                    title=title,
                    slide_count=slide_count
                )
                # Mock模式：使用模拟的流式生成
                accumulated_content = ""
                async for chunk in mock_outline_service.simulate_streaming_outline_call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_config=model_config
                ):
                    # 累积内容用于后续解析
                    accumulated_content += chunk

                    # 发送内容块事件
                    async for event in self.stream_events.send_content_chunk_event(chunk):
                        yield event

                # 使用累积的内容
                ai_response = accumulated_content
            else:
                logger.info(
                    "使用AI服务生成大纲",
                    operation="outline_generation_ai_mode",
                    title=title,
                    slide_count=slide_count
                )
                # AI模式：使用真实的AI服务
                accumulated_content = ""
                async for chunk in self.ai_service.stream_ai_call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_config=model_config
                ):
                    # 累积内容用于后续解析
                    accumulated_content += chunk

                    # 发送内容块事件
                    async for event in self.stream_events.send_content_chunk_event(chunk):
                        yield event

                # 使用累积的内容
                ai_response = accumulated_content

            # 解析AI响应
            raw_markdown = self.helper.parse_ai_response(ai_response)

            # 发送完成事件
            generation_time = time.time() - start_time
            async for event in self.stream_events.send_completion_event(
                "outline_generation",
                {
                    "raw_markdown": raw_markdown,
                    "generation_time": generation_time,
                    "mock_mode": settings.enable_outline_mock
                }
            ):
                yield event


        except Exception as e:
            logger.error(
                "流式生成演示文稿大纲失败",
                operation="outline_stream_generation_failed",
                exception=e,
                title=title,
                slide_count=slide_count,
                mock_mode=settings.enable_outline_mock
            )

            # 发送错误事件
            async for event in self.stream_events.send_error_event(
                e, "OUTLINE_GENERATION_ERROR", "outline_generation"
            ):
                yield event
            raise



