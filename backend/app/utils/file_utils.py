"""
文件工具模块
提供统一的文件处理函数
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Union


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小（字节）
    """
    return os.path.getsize(file_path)


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    获取文件扩展名（小写）

    Args:
        file_path: 文件路径

    Returns:
        str: 文件扩展名（如：.jpg, .png）
    """
    return Path(file_path).suffix.lower()


def is_valid_image_extension(extension: str) -> bool:
    """
    检查是否为有效的图片文件扩展名

    Args:
        extension: 文件扩展名

    Returns:
        bool: 是否为有效的图片扩展名
    """
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    return extension.lower() in valid_extensions


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    计算文件哈希值

    Args:
        file_path: 文件路径
        algorithm: 哈希算法（md5, sha1, sha256）

    Returns:
        str: 文件哈希值
    """
    hash_func = getattr(hashlib, algorithm)()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def ensure_directory_exists(directory_path: Union[str, Path]) -> None:
    """
    确保目录存在，不存在则创建

    Args:
        directory_path: 目录路径
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def safe_delete_file(file_path: Union[str, Path]) -> bool:
    """
    安全删除文件（如果文件存在）

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否成功删除
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def get_mime_type(file_path: Union[str, Path]) -> str:
    """
    根据文件扩展名获取MIME类型

    Args:
        file_path: 文件路径

    Returns:
        str: MIME类型
    """
    extension = get_file_extension(file_path)

    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.zip': 'application/zip',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }

    return mime_map.get(extension, 'application/octet-stream')


def get_human_readable_size(size_bytes: int) -> str:
    """
    将字节大小转换为人类可读的格式

    Args:
        size_bytes: 字节大小

    Returns:
        str: 人类可读的大小（如：1.5 MB）
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def is_file_locked(file_path: Union[str, Path]) -> bool:
    """
    检查文件是否被锁定（正在被其他进程使用）

    Args:
        file_path: 文件路径

    Returns:
        bool: 文件是否被锁定
    """
    try:
        # 尝试以追加模式打开文件
        with open(file_path, 'a'):
            pass
        return False
    except (IOError, OSError):
        return True


def find_files_by_pattern(directory: Union[str, Path], pattern: str) -> list:
    """
    在目录中查找匹配模式的文件

    Args:
        directory: 目录路径
        pattern: 文件模式（支持通配符）

    Returns:
        list: 匹配的文件路径列表
    """
    directory_path = Path(directory)
    return list(directory_path.glob(pattern))


def get_file_creation_time(file_path: Union[str, Path]) -> Optional[float]:
    """
    获取文件创建时间（时间戳）

    Args:
        file_path: 文件路径

    Returns:
        Optional[float]: 创建时间戳，如果文件不存在返回None
    """
    try:
        return os.path.getctime(file_path)
    except OSError:
        return None


def get_file_modification_time(file_path: Union[str, Path]) -> Optional[float]:
    """
    获取文件修改时间（时间戳）

    Args:
        file_path: 文件路径

    Returns:
        Optional[float]: 修改时间戳，如果文件不存在返回None
    """
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return None


def copy_file_with_metadata(source_path: Union[str, Path],
                           target_path: Union[str, Path]) -> bool:
    """
    复制文件并保留元数据

    Args:
        source_path: 源文件路径
        target_path: 目标文件路径

    Returns:
        bool: 是否成功复制
    """
    try:
        import shutil
        shutil.copy2(source_path, target_path)
        return True
    except Exception:
        return False


def get_relative_path(base_path: Union[str, Path],
                     target_path: Union[str, Path]) -> str:
    """
    获取相对于基础路径的相对路径

    Args:
        base_path: 基础路径
        target_path: 目标路径

    Returns:
        str: 相对路径
    """
    base = Path(base_path).resolve()
    target = Path(target_path).resolve()

    try:
        return str(target.relative_to(base))
    except ValueError:
        # 如果目标路径不在基础路径下，返回绝对路径
        return str(target)