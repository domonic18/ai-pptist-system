"""
幻灯片生成Mock服务
提供模拟的幻灯片生成功能，用于开发和调试环境
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class MockSlidesService:
    """幻灯片生成Mock服务类"""

    def __init__(self):
        """初始化Mock服务"""
        self.mock_file_path = Path(settings.absolute_mockdata_dir) / "slides_example.json"
        self._file_available = self.mock_file_path.exists()

        if not self._file_available:
            logger.warning(
                "Mock幻灯片文件不存在，Mock服务将使用默认内容",
                extra={"mock_file_path": str(self.mock_file_path)}
            )

    def _read_mock_slides_content(self) -> List[Dict[str, Any]]:
        """
        读取Mock幻灯片文件内容

        Returns:
            List[Dict[str, Any]]: Mock幻灯片内容列表
        """
        if self._file_available:
            try:
                with open(self.mock_file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    logger.debug(
                        "成功读取Mock幻灯片文件",
                        extra={
                            "file_path": str(self.mock_file_path),
                            "slide_count": len(content)
                        }
                    )
                    return content
            except Exception as e:
                logger.warning(
                    "Mock幻灯片文件读取失败，使用默认内容",
                    extra={
                        "file_path": str(self.mock_file_path),
                        "error": str(e)
                    }
                )
                self._file_available = False

        # 文件不存在或读取失败时返回默认内容
        logger.warning(
            "Mock幻灯片文件不存在，返回默认幻灯片内容",
            extra={"mock_file_path": str(self.mock_file_path)}
        )
        return self._get_default_slides_content()

    def _get_default_slides_content(self) -> List[Dict[str, Any]]:
        """获取默认幻灯片内容"""
        return [
            {
                "type": "cover",
                "data": {
                    "title": "Mock幻灯片文件未配置",
                    "text": f"请检查文件路径: {self.mock_file_path}"
                }
            },
            {
                "type": "contents",
                "data": {
                    "items": ["配置问题", "文件路径", "Mock服务状态"]
                }
            },
            {
                "type": "slide",
                "data": {
                    "title": "配置问题",
                    "content": "Mock幻灯片文件不存在或无法读取，请检查配置文件"
                }
            }
        ]

    async def simulate_streaming_slides_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        模拟幻灯片流式调用

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: 幻灯片事件生成器

        Yields:
            str: 模拟的流式幻灯片事件
        """
        logger.info(
            "开始模拟幻灯片流式生成",
            extra={
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        # 读取Mock幻灯片内容
        slides_content = self._read_mock_slides_content()

        # 模拟流式输出
        for i, slide in enumerate(slides_content):
            # 模拟处理延迟（根据幻灯片序号增加延迟）
            delay = min(settings.mock_slide_delay + (i * 0.05), settings.mock_delay_base)
            await asyncio.sleep(delay)

            # 生成JSON格式的幻灯片事件
            slide_event = json.dumps(slide, ensure_ascii=False)
            yield slide_event


        logger.info("模拟幻灯片流式生成完成")

    async def simulate_slides_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        模拟幻灯片调用（用于批量处理）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            List[Dict[str, Any]]: 完整的幻灯片响应内容列表
        """
        logger.info(
            "开始模拟幻灯片调用",
            extra={
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt)
            }
        )

        # 模拟响应延迟
        await asyncio.sleep(settings.mock_delay_base)

        # 读取Mock幻灯片内容
        content = self._read_mock_slides_content()

        logger.info(
            "模拟幻灯片调用完成",
            extra={"slide_count": len(content)}
        )

        return content


# 全局Mock服务实例
mock_slides_service = MockSlidesService()