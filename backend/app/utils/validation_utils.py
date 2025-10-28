"""
验证工具模块
提供统一的验证函数
"""

import re
from typing import Any, Optional, Union


def is_valid_integer(value: Any) -> bool:
    """
    验证是否为有效的整数

    Args:
        value: 要验证的值

    Returns:
        bool: 是否为有效整数
    """
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_float(value: Any) -> bool:
    """
    验证是否为有效的浮点数

    Args:
        value: 要验证的值

    Returns:
        bool: 是否为有效浮点数
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_boolean(value: Any) -> bool:
    """
    验证是否为有效的布尔值

    Args:
        value: 要验证的值

    Returns:
        bool: 是否为有效布尔值
    """
    return value in [True, False, 'true', 'false', 'True', 'False', 1, 0, '1', '0']


def is_valid_list(value: Any, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """
    验证是否为有效的列表

    Args:
        value: 要验证的值
        min_length: 最小长度
        max_length: 最大长度

    Returns:
        bool: 是否为有效列表
    """
    if not isinstance(value, list):
        return False

    if len(value) < min_length:
        return False

    if max_length is not None and len(value) > max_length:
        return False

    return True


def is_valid_dict(value: Any, required_keys: Optional[list] = None) -> bool:
    """
    验证是否为有效的字典

    Args:
        value: 要验证的值
        required_keys: 必需包含的键

    Returns:
        bool: 是否为有效字典
    """
    if not isinstance(value, dict):
        return False

    if required_keys:
        for key in required_keys:
            if key not in value:
                return False

    return True


def is_valid_hex_color(color: str) -> bool:
    """
    验证是否为有效的十六进制颜色值

    Args:
        color: 颜色值（如：#FF0000）

    Returns:
        bool: 是否为有效颜色值
    """
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    return bool(re.match(pattern, color))


def is_valid_rgb_color(r: int, g: int, b: int) -> bool:
    """
    验证是否为有效的RGB颜色值

    Args:
        r: 红色值（0-255）
        g: 绿色值（0-255）
        b: 蓝色值（0-255）

    Returns:
        bool: 是否为有效RGB颜色值
    """
    return all(0 <= x <= 255 for x in [r, g, b])


def is_valid_percentage(value: Union[int, float]) -> bool:
    """
    验证是否为有效的百分比值

    Args:
        value: 百分比值

    Returns:
        bool: 是否为有效百分比值
    """
    return 0 <= value <= 100


def is_valid_coordinate(x: Union[int, float], y: Union[int, float]) -> bool:
    """
    验证是否为有效的坐标值

    Args:
        x: X坐标
        y: Y坐标

    Returns:
        bool: 是否为有效坐标
    """
    # 坐标可以是任何数值，这里主要检查是否为数字
    return all(isinstance(coord, (int, float)) for coord in [x, y])


def is_valid_dimension(width: Union[int, float], height: Union[int, float]) -> bool:
    """
    验证是否为有效的尺寸值

    Args:
        width: 宽度
        height: 高度

    Returns:
        bool: 是否为有效尺寸
    """
    return all(isinstance(dim, (int, float)) and dim > 0 for dim in [width, height])


def is_valid_file_size(size_bytes: int, max_size_mb: int = 100) -> bool:
    """
    验证文件大小是否在允许范围内

    Args:
        size_bytes: 文件大小（字节）
        max_size_mb: 最大允许大小（MB）

    Returns:
        bool: 文件大小是否有效
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return 0 <= size_bytes <= max_size_bytes


def is_valid_image_dimensions(width: int, height: int,
                             max_width: int = 10000,
                             max_height: int = 10000) -> bool:
    """
    验证图片尺寸是否在允许范围内

    Args:
        width: 图片宽度
        height: 图片高度
        max_width: 最大宽度
        max_height: 最大高度

    Returns:
        bool: 图片尺寸是否有效
    """
    return (1 <= width <= max_width and
            1 <= height <= max_height)


def is_valid_enum_value(value: Any, enum_class: type) -> bool:
    """
    验证是否为有效的枚举值

    Args:
        value: 要验证的值
        enum_class: 枚举类

    Returns:
        bool: 是否为有效枚举值
    """
    try:
        return value in enum_class
    except (TypeError, AttributeError):
        return False


def is_valid_range(start: Union[int, float], end: Union[int, float]) -> bool:
    """
    验证是否为有效的范围

    Args:
        start: 起始值
        end: 结束值

    Returns:
        bool: 是否为有效范围
    """
    return start <= end


def is_valid_ratio(numerator: Union[int, float], denominator: Union[int, float]) -> bool:
    """
    验证是否为有效的比例

    Args:
        numerator: 分子
        denominator: 分母

    Returns:
        bool: 是否为有效比例
    """
    return denominator != 0


def validate_and_convert_bool(value: Any) -> bool:
    """
    验证并转换布尔值

    Args:
        value: 要转换的值

    Returns:
        bool: 转换后的布尔值
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'y']

    if isinstance(value, int):
        return value != 0

    return bool(value)


def validate_and_convert_int(value: Any, default: int = 0) -> int:
    """
    验证并转换整数值

    Args:
        value: 要转换的值
        default: 转换失败时的默认值

    Returns:
        int: 转换后的整数值
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def validate_and_convert_float(value: Any, default: float = 0.0) -> float:
    """
    验证并转换浮点数值

    Args:
        value: 要转换的值
        default: 转换失败时的默认值

    Returns:
        float: 转换后的浮点数值
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default