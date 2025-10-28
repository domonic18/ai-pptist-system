"""
日期时间工具模块
提供统一的日期时间处理函数
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def get_current_timestamp() -> int:
    """获取当前时间戳（秒级）"""
    return int(time.time())


def get_current_timestamp_ms() -> int:
    """获取当前时间戳（毫秒级）"""
    return int(time.time() * 1000)


def format_datetime(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间

    Args:
        dt: 日期时间对象，如果为None则使用当前时间
        format_str: 格式化字符串

    Returns:
        str: 格式化后的日期时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def parse_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析日期时间字符串

    Args:
        datetime_str: 日期时间字符串
        format_str: 格式化字符串

    Returns:
        datetime: 解析后的日期时间对象
    """
    return datetime.strptime(datetime_str, format_str)


def get_today_start() -> datetime:
    """获取今天的开始时间（00:00:00）"""
    now = datetime.now()
    return datetime(now.year, now.month, now.day)


def get_today_end() -> datetime:
    """获取今天的结束时间（23:59:59）"""
    now = datetime.now()
    return datetime(now.year, now.month, now.day, 23, 59, 59)


def get_week_start() -> datetime:
    """获取本周的开始时间（周一00:00:00）"""
    now = datetime.now()
    # 获取本周一
    monday = now - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day)


def get_week_end() -> datetime:
    """获取本周的结束时间（周日23:59:59）"""
    now = datetime.now()
    # 获取本周日
    sunday = now + timedelta(days=6 - now.weekday())
    return datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)


def get_month_start() -> datetime:
    """获取本月的开始时间（1号00:00:00）"""
    now = datetime.now()
    return datetime(now.year, now.month, 1)


def get_month_end() -> datetime:
    """获取本月的结束时间（最后一天23:59:59）"""
    now = datetime.now()
    # 下个月的第一天减去一天就是本月的最后一天
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)

    last_day = next_month - timedelta(days=1)
    return datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59)


def is_within_time_range(start_time: Union[datetime, str],
                        end_time: Union[datetime, str],
                        check_time: Optional[datetime] = None) -> bool:
    """
    检查时间是否在指定范围内

    Args:
        start_time: 开始时间（datetime对象或字符串）
        end_time: 结束时间（datetime对象或字符串）
        check_time: 要检查的时间，如果为None则使用当前时间

    Returns:
        bool: 是否在时间范围内
    """
    if check_time is None:
        check_time = datetime.now()

    # 如果输入是字符串，转换为datetime对象
    if isinstance(start_time, str):
        start_time = parse_datetime(start_time)
    if isinstance(end_time, str):
        end_time = parse_datetime(end_time)

    return start_time <= check_time <= end_time


def format_duration(seconds: int) -> str:
    """
    格式化持续时间（秒数）

    Args:
        seconds: 秒数

    Returns:
        str: 格式化后的持续时间（如：2小时30分钟15秒）
    """
    if seconds < 0:
        return "0秒"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")

    return "".join(parts)


def get_time_diff(start_time: datetime, end_time: Optional[datetime] = None) -> timedelta:
    """
    计算两个时间之间的差值

    Args:
        start_time: 开始时间
        end_time: 结束时间，如果为None则使用当前时间

    Returns:
        timedelta: 时间差值
    """
    if end_time is None:
        end_time = datetime.now()
    return end_time - start_time


def is_expired(expire_time: Union[datetime, str],
              check_time: Optional[datetime] = None) -> bool:
    """
    检查是否已过期

    Args:
        expire_time: 过期时间（datetime对象或字符串）
        check_time: 要检查的时间，如果为None则使用当前时间

    Returns:
        bool: 是否已过期
    """
    if check_time is None:
        check_time = datetime.now()

    # 如果输入是字符串，转换为datetime对象
    if isinstance(expire_time, str):
        expire_time = parse_datetime(expire_time)

    return check_time > expire_time


def format_datetime_iso(dt: Optional[datetime] = None) -> str:
    """
    格式化日期时间为ISO字符串

    Args:
        dt: 日期时间对象，如果为None则使用当前时间（UTC）

    Returns:
        str: ISO格式的日期时间字符串
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


def get_current_iso_string() -> str:
    """
    获取当前时间的ISO字符串（UTC）

    Returns:
        str: 当前时间的ISO格式字符串
    """
    return datetime.now(timezone.utc).isoformat()