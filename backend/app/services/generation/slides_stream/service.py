"""
幻灯片流式生成服务
负责流式生成演示文稿幻灯片内容
支持Mock模式用于开发和调试环境
"""

import json
import time
from typing import AsyncGenerator, Dict, Any, Optional

from app.core.log_utils import get_logger
from app.core.config import settings
from app.prompts import get_prompt_manager
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.services.generation.banana_generation.stream.common_utils import StreamEventGenerator, StreamJsonParser
from app.utils import ResponseParser
from app.prompts import PromptHelper
from app.services.generation.banana_generation.stream.mock_slides import mock_slides_service

logger = get_logger(__name__)


class SlidesStreamService:
    """幻灯片流式生成服务"""

    def __init__(self):
        """初始化幻灯片流式生成服务"""
        self.prompt_manager = get_prompt_manager()

        # 初始化通用工具
        self.stream_events = StreamEventGenerator()
        self.prompt_helper = PromptHelper(self.prompt_manager)
        self.response_parser = ResponseParser()
        self.stream_json_parser = StreamJsonParser()

    async def generate_slides_stream(
        self,
        content: str,
        language: str = "zh-CN",
        style: str = "professional",
        ai_model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成演示文稿幻灯片内容

        Args:
            content: 原始Markdown大纲内容
            language: 输出语言
            style: 演示文稿风格
            ai_model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: SSE事件生成器
        """
        start_time = time.time()


        try:
            # 发送开始事件
            async for event in self.stream_events.send_start_event(
                "slides_generation",
                {
                    "content_length": len(content),
                    "language": language,
                    "style": style,
                    "mock_mode": settings.enable_slides_mock
                }
            ):
                yield event

            # 渲染提示词和配置
            system_prompt, user_prompt, temperature, max_tokens = \
                self.prompt_helper.prepare_prompts(
                    "presentation",
                    "slides_generation",
                    {
                        "content": content,  # 直接使用原始的Markdown内容
                        "language": language,
                        "style": style
                    },
                    {
                        "language": language,
                        "style": style
                    }
                )

            # 发送提示词准备完成事件
            async for event in self.stream_events.send_prompt_ready_event(
                system_prompt, user_prompt, temperature, max_tokens
            ):
                yield event

            # 根据配置选择使用AI服务还是Mock服务
            if settings.enable_slides_mock:
                logger.info(
                    "使用Mock模式生成幻灯片",
                    operation="slides_generation_mock_mode",
                    content_length=len(content),
                    language=language,
                    style=style
                )
                # Mock模式：使用模拟的流式生成
                generated_slides = []
                async for slide_event in mock_slides_service.simulate_streaming_slides_call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    ai_model_config=ai_model_config
                ):
                    # 直接发送幻灯片事件
                    yield slide_event

                    # 解析事件内容用于统计
                    try:
                        slide_obj = json.loads(slide_event)
                        if isinstance(slide_obj, dict) and 'type' in slide_obj:
                            generated_slides.append(slide_obj)
                    except json.JSONDecodeError:
                        logger.warning("Mock幻灯片事件JSON解析失败")
            else:
                logger.info(
                    "使用AI服务生成幻灯片",
                    operation="slides_generation_ai_mode",
                    content_length=len(content),
                    language=language,
                    style=style
                )
                # AI模式：使用新的统一AI架构
                accumulated_content = ""
                generated_slides = []

                # 使用新的统一AI架构 - 从前端传来的配置获取provider
                if ai_model_config:
                    # 优先从provider_mapping获取chat的provider
                    provider_mapping = ai_model_config.get('provider_mapping', {})
                    provider_name = provider_mapping.get('chat') or ai_model_config.get('provider', 'openai_compatible')
                else:
                    provider_name = 'openai_compatible'
                
                chat_provider = AIProviderFactory.create_provider(
                    capability=ModelCapability.CHAT,
                    provider_name=provider_name,
                    model_config=ai_model_config or {}
                )
                
                # 构建消息列表
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # 调用流式chat接口（使用统一的chat方法，stream=True）
                # 先await获取异步生成器，然后async for迭代
                stream_generator = await chat_provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in stream_generator:
                    # 累积内容
                    accumulated_content += chunk

                    # 尝试从累积内容中提取完整的JSON对象
                    complete_objects, remaining_content = self.stream_json_parser.extract_complete_json_objects(accumulated_content)

                    # 发送找到的完整幻灯片对象
                    for slide_obj in complete_objects:
                        # 验证是否为有效的幻灯片对象
                        if isinstance(slide_obj, dict) and 'type' in slide_obj:
                            # 发送单个幻灯片对象
                            yield json.dumps(slide_obj, ensure_ascii=False)
                            generated_slides.append(slide_obj)

                    # 更新累积内容为剩余未处理的内容
                    accumulated_content = remaining_content

                # 处理最后可能剩余的完整对象
                if accumulated_content.strip():
                    complete_objects, _ = self.stream_json_parser.extract_complete_json_objects(accumulated_content)

                    for slide_obj in complete_objects:
                        if isinstance(slide_obj, dict) and 'type' in slide_obj:
                            yield json.dumps(slide_obj, ensure_ascii=False)
                            generated_slides.append(slide_obj)

            # 发送完成事件
            generation_time = time.time() - start_time
            async for event in self.stream_events.send_completion_event(
                "slides_generation",
                {
                    "total_slides": len(generated_slides),
                    "generation_time": generation_time,
                    "mock_mode": settings.enable_slides_mock
                }
            ):
                yield event


        except Exception as e:
            logger.error(
                "流式生成演示文稿幻灯片失败",
                operation="slides_stream_generation_failed",
                exception=e,
                mock_mode=settings.enable_slides_mock
            )

            # 发送错误事件
            async for event in self.stream_events.send_error_event(
                e, "SLIDES_GENERATION_ERROR", "slides_generation"
            ):
                yield event
            raise
