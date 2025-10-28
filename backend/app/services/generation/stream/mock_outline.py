"""
大纲生成Mock服务
提供模拟的大纲生成功能，用于开发和调试环境
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MockOutlineService:
    """大纲生成Mock服务类"""

    def __init__(self):
        """初始化Mock服务"""
        self.mock_file_path = Path(settings.absolute_mockdata_dir) / "outline_example.md"
        self._file_available = self.mock_file_path.exists()

        if not self._file_available:
            logger.warning(
                "Mock大纲文件不存在，Mock服务将使用默认内容",
                extra={"mock_file_path": str(self.mock_file_path)}
            )

    def _read_mock_outline_content(self) -> str:
        """
        读取Mock大纲文件内容

        Returns:
            str: Mock大纲内容
        """
        if self._file_available:
            try:
                with open(self.mock_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.debug(
                        "成功读取Mock大纲文件",
                        extra={
                            "file_path": str(self.mock_file_path),
                            "content_length": len(content)
                        }
                    )
                    return content
            except Exception as e:
                logger.warning(
                    "Mock大纲文件读取失败，返回空内容",
                    extra={
                        "file_path": str(self.mock_file_path),
                        "error": str(e)
                    }
                )
                self._file_available = False

        # 文件不存在或读取失败时返回空内容
        logger.warning(
            "Mock大纲文件不存在，返回空markdown内容",
            extra={"mock_file_path": str(self.mock_file_path)}
        )
        return "# Mock大纲文件未配置\n\n请检查文件路径: " + str(self.mock_file_path)

    async def simulate_streaming_outline_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        模拟大纲流式调用

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            AsyncGenerator[str, None]: 内容块生成器

        Yields:
            str: 模拟的流式内容块
        """
        logger.info(
            "开始模拟大纲流式生成",
            extra={
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        # 读取Mock大纲内容
        markdown_content = self._read_mock_outline_content()

        # 模拟流式输出
        lines = markdown_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip():  # 只发送非空行
                # 模拟处理延迟（根据行号增加延迟，模拟真实AI响应）
                delay = min(0.05 + (i * 0.01), settings.mock_delay_base)
                await asyncio.sleep(delay)

                # 添加换行符并返回
                yield line + '\n'

        logger.info("模拟大纲流式生成完成")

    async def simulate_outline_call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        model_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        模拟大纲调用（用于最终解析）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model_config: 模型配置

        Returns:
            str: 完整的大纲响应内容
        """
        logger.info(
            "开始模拟大纲调用",
            extra={
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt)
            }
        )

        # 模拟响应延迟
        await asyncio.sleep(settings.mock_delay_base)

        # 读取Mock大纲内容
        content = self._read_mock_outline_content()

        logger.info(
            "模拟大纲调用完成",
            extra={"content_length": len(content)}
        )

        return content


# 全局Mock服务实例
mock_outline_service = MockOutlineService()