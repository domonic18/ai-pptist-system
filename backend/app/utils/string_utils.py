"""
字符串工具模块
提供统一的字符串处理函数
"""

import re
from typing import List, Optional


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串，如果超过最大长度则添加后缀

    Args:
        text: 要截断的字符串
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        str: 截断后的字符串
    """
    if len(text) <= max_length:
        return text

    if max_length <= len(suffix):
        return suffix[:max_length]

    return text[:max_length - len(suffix)] + suffix


def remove_extra_spaces(text: str) -> str:
    """
    移除字符串中多余的空格

    Args:
        text: 要处理的字符串

    Returns:
        str: 处理后的字符串
    """
    # 移除首尾空格，并将多个连续空格替换为单个空格
    return re.sub(r'\s+', ' ', text.strip())


def is_valid_email(email: str) -> bool:
    """
    验证邮箱格式是否有效

    Args:
        email: 要验证的邮箱地址

    Returns:
        bool: 是否为有效邮箱
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """
    验证URL格式是否有效

    Args:
        url: 要验证的URL

    Returns:
        bool: 是否为有效URL
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def camel_to_snake(camel_str: str) -> str:
    """
    将驼峰命名转换为蛇形命名

    Args:
        camel_str: 驼峰命名字符串

    Returns:
        str: 蛇形命名字符串
    """
    # 在大写字母前插入下划线，并转换为小写
    snake_str = re.sub('([A-Z])', r'_\1', camel_str)
    # 移除开头的下划线（如果有）
    return snake_str.lower().lstrip('_')


def snake_to_camel(snake_str: str) -> str:
    """
    将蛇形命名转换为驼峰命名

    Args:
        snake_str: 蛇形命名字符串

    Returns:
        str: 驼峰命名字符串
    """
    # 将下划线后的字母转换为大写
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def extract_numbers(text: str) -> List[int]:
    """
    从字符串中提取所有数字

    Args:
        text: 要提取数字的字符串

    Returns:
        List[int]: 提取到的数字列表
    """
    numbers = re.findall(r'\d+', text)
    return [int(num) for num in numbers]


def extract_emails(text: str) -> List[str]:
    """
    从字符串中提取所有邮箱地址

    Args:
        text: 要提取邮箱的字符串

    Returns:
        List[str]: 提取到的邮箱地址列表
    """
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def extract_urls(text: str) -> List[str]:
    """
    从字符串中提取所有URL

    Args:
        text: 要提取URL的字符串

    Returns:
        List[str]: 提取到的URL列表
    """
    pattern = r'https?://[^\s]+'
    return re.findall(pattern, text)


def count_words(text: str) -> int:
    """
    统计字符串中的单词数量

    Args:
        text: 要统计的字符串

    Returns:
        int: 单词数量
    """
    # 使用正则表达式分割单词
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def is_contains_chinese(text: str) -> bool:
    """
    检查字符串是否包含中文字符

    Args:
        text: 要检查的字符串

    Returns:
        bool: 是否包含中文字符
    """
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def is_contains_english(text: str) -> bool:
    """
    检查字符串是否包含英文字符

    Args:
        text: 要检查的字符串

    Returns:
        bool: 是否包含英文字符
    """
    return bool(re.search(r'[a-zA-Z]', text))


def normalize_filename(filename: str) -> str:
    """
    规范化文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        str: 规范化后的文件名
    """
    # 移除非法字符（Windows和Unix都支持的字符）
    illegal_chars = r'[<>:"/\\|?*]'
    normalized = re.sub(illegal_chars, '_', filename)

    # 移除首尾空格和点
    normalized = normalized.strip().strip('.')

    # 如果文件名为空，使用默认名称
    if not normalized:
        normalized = 'unnamed_file'

    return normalized


def generate_slug(text: str, max_length: int = 50) -> str:
    """
    生成URL友好的slug

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        str: 生成的slug
    """
    # 转换为小写
    slug = text.lower()

    # 移除特殊字符，只保留字母、数字、空格和连字符
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)

    # 将空格替换为连字符
    slug = re.sub(r'\s+', '-', slug)

    # 移除多余的连字符
    slug = re.sub(r'-+', '-', slug)

    # 截断到最大长度
    if len(slug) > max_length:
        # 在连字符处截断
        if '-' in slug:
            parts = slug.split('-')
            result = []
            current_length = 0

            for part in parts:
                if current_length + len(part) + 1 <= max_length:
                    result.append(part)
                    current_length += len(part) + 1
                else:
                    break

            slug = '-'.join(result)
        else:
            slug = slug[:max_length]

    return slug.strip('-')


def mask_sensitive_info(text: str, sensitive_keys: List[str] = None) -> str:
    """
    屏蔽敏感信息（如密码、API密钥等）

    Args:
        text: 包含敏感信息的文本
        sensitive_keys: 敏感关键词列表

    Returns:
        str: 屏蔽敏感信息后的文本
    """
    if sensitive_keys is None:
        sensitive_keys = ['password', 'api_key', 'secret', 'token']

    masked_text = text

    for key in sensitive_keys:
        # 匹配 key=value 格式
        pattern = rf'({key}[=:]\s*)([^\s&,]+)'
        masked_text = re.sub(pattern, rf'\1***', masked_text, flags=re.IGNORECASE)

    return masked_text