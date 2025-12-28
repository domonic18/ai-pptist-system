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
from app.services.generation.banana_generation.stream.outline_helper import OutlineHelper
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.services.generation.banana_generation.stream.common_utils import StreamEventGenerator
from app.prompts import PromptHelper
from app.services.generation.banana_generation.stream.mock_outline import mock_outline_service
from app.repositories.ai_model import AIModelRepository

logger = get_logger(__name__)


class OutlineStreamService:
    """大纲流式生成服务"""

    def __init__(self, ai_model_repo: AIModelRepository):
        """
        初始化大纲流式生成服务
        
        Args:
            ai_model_repo: AI模型仓储（依赖注入）
        """
        self.prompt_manager = get_prompt_manager()
        self.helper = OutlineHelper()
        self.ai_model_repo = ai_model_repo

        # 初始化通用工具
        self.stream_events = StreamEventGenerator()
        self.prompt_helper = PromptHelper(self.prompt_manager)

    async def generate_outline_stream(
        self,
        title: str,
        input_content: Optional[str] = None,
        slide_count: int = 8,
        language: str = "zh-CN",
        ai_model_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成演示文稿大纲

        Args:
            title: 演示文稿标题
            input_content: 输入内容或提示
            slide_count: 幻灯片数量
            language: 输出语言
            ai_model_id: 模型ID（从数据库查询完整配置）

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
                    max_tokens=max_tokens
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
                    slide_count=slide_count,
                    ai_model_id=ai_model_id
                )
                # AI模式：使用新的统一AI架构
                accumulated_content = ""
                
                # 从数据库查询模型配置
                if not ai_model_id:
                    raise ValueError("AI模型ID不能为空")
                
                ai_model = await self.ai_model_repo.get_model_by_id(ai_model_id)
                if not ai_model:
                    raise ValueError(f"未找到模型: {ai_model_id}")
                
                if not ai_model.is_enabled:
                    raise ValueError(f"模型已禁用: {ai_model.name}")
                
                # 检查模型是否支持chat能力
                if 'chat' not in ai_model.capabilities:
                    raise ValueError(f"模型不支持chat能力: {ai_model.name}")
                
                # 获取provider名称
                provider_mapping = ai_model.provider_mapping or {}
                provider_name = provider_mapping.get('chat', 'openai_compatible')
                
                # 构建模型配置
                model_config = {
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
                    "创建AI Provider",
                    operation="create_ai_provider",
                    provider_name=provider_name,
                    model_id=ai_model.id,
                    model_name=ai_model.ai_model_name,
                    base_url=ai_model.base_url,
                    api_key_length=len(ai_model.api_key) if ai_model.api_key else 0,
                    has_api_key=bool(ai_model.api_key)
                )
                
                chat_provider = AIProviderFactory.create_provider(
                    capability=ModelCapability.CHAT,
                    provider_name=provider_name,
                    model_config=model_config
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



