"""
ID生成工具模块
提供统一的ID生成方法，支持多种ID格式
"""

import uuid
import time
import random
import string
from typing import Optional


def generate_uuid() -> str:
    """生成标准UUID字符串"""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    生成短ID（基于时间戳和随机数）

    Args:
        length: ID长度，默认8位

    Returns:
        str: 短ID字符串
    """
    if length < 4:
        raise ValueError("ID长度不能小于4位")

    # 使用时间戳和随机数生成ID
    timestamp = int(time.time() * 1000)
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length-4))

    # 将时间戳转换为36进制缩短长度
    timestamp_base36 = base36_encode(timestamp)

    # 组合时间戳和随机部分
    return f"{timestamp_base36[:4]}{random_part}"


def generate_numeric_id(length: int = 10) -> str:
    """
    生成纯数字ID

    Args:
        length: ID长度，默认10位

    Returns:
        str: 数字ID字符串
    """
    if length < 6:
        raise ValueError("数字ID长度不能小于6位")

    timestamp = int(time.time() * 1000)
    random_part = ''.join(random.choices(string.digits, k=length-6))

    # 使用时间戳的后6位
    timestamp_str = str(timestamp)[-6:]

    return f"{timestamp_str}{random_part}"


def base36_encode(number: int) -> str:
    """
    将数字转换为36进制字符串

    Args:
        number: 要转换的数字

    Returns:
        str: 36进制字符串
    """
    if number == 0:
        return "0"

    base36 = ""
    base36_chars = string.digits + string.ascii_lowercase

    while number:
        number, remainder = divmod(number, 36)
        base36 = base36_chars[remainder] + base36

    return base36


def is_valid_uuid(uuid_string: str) -> bool:
    """
    验证字符串是否为有效的UUID

    Args:
        uuid_string: 要验证的字符串

    Returns:
        bool: 是否为有效UUID
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def generate_id_with_prefix(prefix: str, id_type: str = "uuid") -> str:
    """
    生成带前缀的ID

    Args:
        prefix: ID前缀（如"img", "ppt", "user"等）
        id_type: ID类型，支持"uuid"、"short"、"numeric"

    Returns:
        str: 带前缀的ID
    """
    if id_type == "uuid":
        id_part = generate_uuid()
    elif id_type == "short":
        id_part = generate_short_id()
    elif id_type == "numeric":
        id_part = generate_numeric_id()
    else:
        raise ValueError(f"不支持的ID类型: {id_type}")

    return f"{prefix}_{id_part}"


# 常用ID前缀的快捷方法
def generate_image_id() -> str:
    """生成图片ID"""
    return generate_id_with_prefix("img", "uuid")


def generate_presentation_id() -> str:
    """生成演示文稿ID"""
    return generate_id_with_prefix("ppt", "uuid")


def generate_user_id() -> str:
    """生成用户ID"""
    return generate_id_with_prefix("user", "uuid")


def generate_session_id() -> str:
    """生成会话ID"""
    return generate_id_with_prefix("session", "short")