"""
测试专用的 mock 工具和辅助函数
提供常用的 mock 对象和装饰器，供所有测试使用
"""

import functools
from typing import Any, Dict, Optional, Callable
from unittest.mock import MagicMock, patch


class MockBuilder:
    """Mock对象构建器 - 用于创建常用的mock对象"""

    @staticmethod
    def create_mock_cos_service():
        """创建COS存储服务的mock对象"""
        mock = MagicMock()

        # 模拟COS文件操作
        mock.upload_file.return_value = {
            "success": True,
            "cos_key": "test-cos-key",
            "url": "https://test-bucket.cos.test-region.myqcloud.com/test-cos-key",
            "etag": "test-etag",
            "size": 1024,
            "uploaded_at": "2023-01-01T00:00:00"
        }
        mock.delete_file.return_value = True
        mock.file_exists.return_value = True
        mock.generate_presigned_url.return_value = "https://presigned-url.com"
        mock.get_file_metadata.return_value = {
            'content_type': 'image/jpeg',
            'content_length': 1024,
            'etag': 'test-etag',
            'last_modified': '2023-01-01T00:00:00',
            'metadata': {}
        }
        mock.generate_cos_key.return_value = "images/test-user/test-file.jpg"

        return mock

    @staticmethod
    def create_mock_image_service():
        """创建图片服务的mock对象"""
        mock = MagicMock()

        # 模拟图片服务操作
        mock.create_image.return_value = MagicMock(
            id="test-image-id",
            user_id="test-user",
            image_url="https://test-url.com/image.jpg",
            original_filename="test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            storage_status="active"
        )
        mock.get_image.return_value = MagicMock(
            id="test-image-id",
            user_id="test-user",
            image_url="https://test-url.com/image.jpg",
            original_filename="test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            storage_status="active"
        )
        mock.list_images.return_value = {
            "items": [],
            "total": 0,
            "skip": 0,
            "limit": 20,
            "has_more": False
        }
        mock.update_image.return_value = MagicMock(
            id="test-image-id",
            user_id="test-user",
            image_url="https://test-url.com/image.jpg",
            original_filename="test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            storage_status="active"
        )
        mock.delete_image.return_value = True

        return mock

    @staticmethod
    def create_mock_db_session():
        """创建数据库会话的mock对象"""
        mock = MagicMock()

        # 模拟数据库操作
        mock.commit.return_value = None
        mock.rollback.return_value = None
        mock.close.return_value = None

        return mock


def mock_config(test_config: Dict[str, Any]) -> Callable:
    """
    装饰器：mock配置
    用于替换app.core.config.settings

    Args:
        test_config: 测试配置字典

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        @patch("app.core.config.settings")
        def wrapper(mock_settings, *args, **kwargs):
            # 设置mock配置
            for key, value in test_config.items():
                setattr(mock_settings, key, value)
            return func(mock_settings, *args, **kwargs)
        return wrapper
    return decorator


def mock_dependency(target: str) -> Callable:
    """
    装饰器：mock依赖注入
    用于替换FastAPI的Depends注入

    Args:
        target: 要mock的目标路径

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        @patch(target)
        def wrapper(mock_dep, *args, **kwargs):
            return func(mock_dep, *args, **kwargs)
        return wrapper
    return decorator