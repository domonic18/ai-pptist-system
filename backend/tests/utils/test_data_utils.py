"""
测试数据生成和验证工具
提供常用的测试数据生成函数和验证器
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_image_data(
        user_id: str = "test-user",
        filename: str = "test.jpg",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """生成图片测试数据"""
        return {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "original_filename": filename,
            "file_size": 1024,
            "mime_type": "image/jpeg",
            "image_url": f"https://test-bucket.cos.test-region.myqcloud.com/images/{user_id}/{filename}",
            "description": description or "测试图片描述",
            "tags": tags or ["test", "image"],
            "source_type": "upload",
            "storage_status": "active",
            "cos_key": f"images/{user_id}/{filename}",
            "cos_bucket": "test-bucket",
            "cos_region": "test-region",
            "is_public": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    @staticmethod
    def generate_user_data(
        user_id: str = "test-user",
        email: str = "test@example.com",
        name: str = "测试用户"
    ) -> Dict[str, Any]:
        """生成用户测试数据"""
        return {
            "id": user_id,
            "email": email,
            "name": name,
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    @staticmethod
    def generate_presigned_url_request(
        filename: str = "test.jpg",
        content_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """生成预签名URL请求测试数据"""
        return {
            "filename": filename,
            "content_type": content_type
        }

    @staticmethod
    def generate_upload_response(
        image_id: str = "test-image-id",
        filename: str = "test.jpg"
    ) -> Dict[str, Any]:
        """生成上传响应测试数据"""
        return {
            "success": True,
            "image_id": image_id,
            "image_url": f"https://test-bucket.cos.test-region.myqcloud.com/images/test-user/{filename}",
            "cos_key": f"images/test-user/{filename}",
            "message": "图片上传成功"
        }


class TestDataValidator:
    """测试数据验证器"""

    @staticmethod
    def validate_image_data(image_data: Dict[str, Any]) -> bool:
        """验证图片数据格式"""
        required_fields = [
            "id", "user_id", "original_filename", "file_size",
            "mime_type", "image_url", "storage_status", "created_at"
        ]

        for field in required_fields:
            if field not in image_data:
                return False

        return True

    @staticmethod
    def validate_upload_response(response_data: Dict[str, Any]) -> bool:
        """验证上传响应格式"""
        required_fields = ["success", "image_id", "image_url", "cos_key", "message"]

        for field in required_fields:
            if field not in response_data:
                return False

        return response_data["success"] is True

    @staticmethod
    def validate_presigned_response(response_data: Dict[str, Any]) -> bool:
        """验证预签名响应格式"""
        required_fields = ["success", "upload_url", "cos_key", "access_url", "expires_in", "message"]

        for field in required_fields:
            if field not in response_data:
                return False

        return response_data["success"] is True