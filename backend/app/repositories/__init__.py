"""
Repository模块
包含所有数据访问层的Repository类
"""

from .base import BaseRepository
from .image import ImageRepository

__all__ = [
    'BaseRepository',
    'ImageRepository'
]