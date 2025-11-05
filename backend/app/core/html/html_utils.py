"""
HTML处理工具模块
包含HTML转换器和解析器共享的工具函数
"""

import re
from typing import Dict, Optional


def parse_inline_style(style_str: str) -> Dict[str, str]:
    """
    解析内联样式字符串为字典

    Args:
        style_str: 样式字符串，如 "position: absolute; left: 100px"

    Returns:
        Dict[str, str]: 样式字典
    """
    style_dict = {}
    if not style_str:
        return style_dict

    for item in style_str.split(';'):
        item = item.strip()
        if ':' in item:
            key, value = item.split(':', 1)
            style_dict[key.strip()] = value.strip()

    return style_dict


def parse_px_value(value: str, default: float = 0.0) -> float:
    """
    解析px值，支持auto等特殊值

    Args:
        value: 如 "100px" 或 "100" 或 "auto"
        default: 当无法解析时返回的默认值

    Returns:
        float: 数值
    """
    if not value:
        return default

    value = str(value).strip().lower()

    # 如果是auto或其他非数值，返回默认值
    if value == 'auto' or value == 'inherit' or value == 'initial':
        return default

    # 移除px后缀
    if value.endswith('px'):
        value = value[:-2]

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_rotate_value(transform: str) -> float:
    """
    从transform中解析旋转角度

    Args:
        transform: 如 "rotate(15deg)"

    Returns:
        float: 角度值
    """
    if not transform:
        return 0.0

    match = re.search(r'rotate\s*\(\s*([-\d.]+)deg\s*\)', transform)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass

    return 0.0


def parse_radius_value(radius_str: str) -> Optional[float]:
    """
    解析border-radius值

    Args:
        radius_str: CSS border-radius值，如 "10px" 或 "10px 20px"

    Returns:
        Optional[float]: 圆角半径值，如果无法解析则返回None
    """
    if not radius_str:
        return None

    radius_str = str(radius_str).strip().lower()

    # 处理多个值的情况（如 "10px 20px"），取第一个值
    parts = radius_str.split()
    if parts:
        first_value = parts[0]

        # 移除px后缀
        if first_value.endswith('px'):
            first_value = first_value[:-2]

        try:
            return float(first_value)
        except (ValueError, TypeError):
            pass

    return None


def parse_shadow_style(shadow_dict: Optional[Dict]) -> Optional[str]:
    """
    解析阴影样式字典为CSS字符串

    Args:
        shadow_dict: 阴影样式字典

    Returns:
        Optional[str]: CSS box-shadow字符串
    """
    if not shadow_dict:
        return None

    shadow_styles = []
    if shadow_dict.get('color'):
        shadow_styles.append(shadow_dict['color'])
    if shadow_dict.get('h') is not None:
        shadow_styles.append(f"{shadow_dict['h']}px")
    if shadow_dict.get('v') is not None:
        shadow_styles.append(f"{shadow_dict['v']}px")
    if shadow_dict.get('blur') is not None:
        shadow_styles.append(f"{shadow_dict['blur']}px")
    if shadow_dict.get('spread') is not None:
        shadow_styles.append(f"{shadow_dict['spread']}px")

    return " ".join(shadow_styles) if shadow_styles else None


def parse_filter_style(filter_dict: Optional[Dict]) -> Optional[str]:
    """
    解析滤镜样式字典为CSS字符串

    Args:
        filter_dict: 滤镜样式字典

    Returns:
        Optional[str]: CSS filter字符串
    """
    if not filter_dict:
        return None

    filter_styles = []
    if filter_dict.get('brightness') is not None:
        filter_styles.append(f"brightness({filter_dict['brightness']}%)")
    if filter_dict.get('contrast') is not None:
        filter_styles.append(f"contrast({filter_dict['contrast']}%)")
    if filter_dict.get('saturation') is not None:
        filter_styles.append(f"saturate({filter_dict['saturation']}%)")
    if filter_dict.get('hue') is not None:
        filter_styles.append(f"hue-rotate({filter_dict['hue']}deg)")
    if filter_dict.get('blur') is not None:
        filter_styles.append(f"blur({filter_dict['blur']}px)")

    return " ".join(filter_styles) if filter_styles else None


def parse_outline_style(outline_data) -> Optional[Dict[str, str]]:
    """
    解析轮廓样式数据

    Args:
        outline_data: 轮廓数据，可能是字符串或字典

    Returns:
        Optional[Dict[str, str]]: 轮廓样式字典
    """
    if not outline_data:
        return None

    if isinstance(outline_data, dict):
        return outline_data
    elif isinstance(outline_data, str):
        # 解析字符串格式的轮廓
        match = re.match(r'(\d+)px\s+(\w+)\s+(#[0-9a-fA-F]{3,6})', outline_data)
        if match:
            return {
                'width': match.group(1),
                'style': match.group(2),
                'color': match.group(3)
            }

    return None