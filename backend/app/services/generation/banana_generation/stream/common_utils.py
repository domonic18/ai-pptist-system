"""
流式生成通用工具函数
提供流式AI生成过程中通用的函数和工具
"""

import json
import time
from typing import AsyncGenerator, Dict, Any, Optional


class StreamEventGenerator:
    """流式事件生成器"""

    @staticmethod
    async def send_start_event(
        operation_type: str,
        data: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """发送开始事件"""
        data["timestamp"] = time.time()
        data["operation_type"] = operation_type
        yield json.dumps({
            "event": "start",
            "data": data
        }, ensure_ascii=False)

    @staticmethod
    async def send_prompt_ready_event(
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """发送提示词准备完成事件"""
        yield json.dumps({
            "event": "prompt_ready",
            "data": {
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timestamp": time.time()
            }
        }, ensure_ascii=False)

    @staticmethod
    async def send_content_chunk_event(chunk: str) -> AsyncGenerator[str, None]:
        """发送内容块事件"""
        yield json.dumps({
            "event": "content_chunk",
            "data": {
                "chunk": chunk,
                "timestamp": time.time()
            }
        }, ensure_ascii=False)

    @staticmethod
    async def send_completion_event(
        operation_type: str,
        data: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """发送完成事件"""
        data["timestamp"] = time.time()
        data["operation_type"] = operation_type
        yield json.dumps({
            "event": "complete",
            "data": data
        }, ensure_ascii=False)

    @staticmethod
    async def send_error_event(
        error: Exception,
        error_code: str,
        operation_type: str
    ) -> AsyncGenerator[str, None]:
        """发送错误事件"""
        yield json.dumps({
            "event": "error",
            "data": {
                "error": str(error),
                "code": error_code,
                "operation_type": operation_type,
                "timestamp": time.time()
            }
        }, ensure_ascii=False)


class StreamJsonParser:
    """流式JSON解析器"""

    @staticmethod
    def find_json_end(content: str, start_pos: int) -> Optional[int]:
        """
        使用括号平衡算法查找JSON对象的结束位置

        Args:
            content: 要搜索的内容
            start_pos: JSON对象的起始位置

        Returns:
            Optional[int]: JSON对象的结束位置，如果未找到完整对象则返回None
        """
        if start_pos >= len(content):
            return None

        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(content[start_pos:], start_pos):
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1

                # 当所有括号都匹配时，找到了完整的JSON对象
                if brace_count == 0 and bracket_count == 0 and i > start_pos:
                    return i

        return None

    @staticmethod
    def extract_complete_json_objects(content: str) -> tuple[list[dict], str]:
        """
        从流式内容中提取完整的JSON对象

        Args:
            content: 累积的流式内容

        Returns:
            tuple: (完整的JSON对象列表, 剩余未处理的内容)
        """
        import re

        complete_objects = []

        # 移除markdown代码块标记
        cleaned_content = re.sub(r'```json\s*', '', content)
        cleaned_content = re.sub(r'\s*```', '', cleaned_content)
        cleaned_content = cleaned_content.strip()

        if not cleaned_content:
            return complete_objects, content

        # 使用更健壮的解析方法：逐个字符扫描，找到所有完整的JSON对象
        remaining_content = cleaned_content
        processed_content = ""

        while remaining_content:
            # 查找第一个JSON对象开始位置
            start_match = re.search(r'\{', remaining_content)
            if not start_match:
                break

            start_pos = start_match.start()

            # 使用括号平衡算法检测完整的JSON对象
            json_end_pos = StreamJsonParser.find_json_end(remaining_content, start_pos)

            if json_end_pos is not None:
                # 提取JSON字符串
                json_str = remaining_content[start_pos:json_end_pos + 1].strip()

                try:
                    # 尝试解析JSON
                    json_obj = json.loads(json_str)

                    # 验证并处理JSON对象
                    if isinstance(json_obj, dict):
                        # 情况1：直接的slide对象（包含type字段）
                        if 'type' in json_obj:
                            complete_objects.append(json_obj)
                        # 情况2：包含slides数组的对象
                        elif 'slides' in json_obj and isinstance(json_obj['slides'], list):
                            # 提取slides数组中的每个slide对象
                            for slide in json_obj['slides']:
                                if isinstance(slide, dict) and 'type' in slide:
                                    complete_objects.append(slide)

                    # 更新已处理的内容
                    processed_content += remaining_content[:json_end_pos + 1]
                    remaining_content = remaining_content[json_end_pos + 1:].lstrip()

                except json.JSONDecodeError:
                    # 如果解析失败，保留这部分内容到下一次处理
                    processed_content += remaining_content[:start_pos + 1]
                    remaining_content = remaining_content[start_pos + 1:]
            else:
                # 没有找到完整的JSON对象，保留剩余内容
                break

        # 返回未处理的内容（可能是部分JSON对象）
        return complete_objects, remaining_content
