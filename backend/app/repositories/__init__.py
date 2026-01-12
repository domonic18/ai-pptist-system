"""
Repository模块
包含所有数据访问层的Repository类
"""

from .base import BaseRepository
from .image import ImageRepository
from .user import UserRepository
from .user_session import UserSessionRepository
from .login_history import LoginHistoryRepository

__all__ = [
    'BaseRepository',
    'ImageRepository',
    'UserRepository',
    'UserSessionRepository',
    'LoginHistoryRepository',
]