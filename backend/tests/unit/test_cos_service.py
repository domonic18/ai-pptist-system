"""
COS服务单元测试
测试COSService类的所有方法
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os
from datetime import datetime, timedelta

from app.core.storage import COSStorage
from app.core.config import settings
from app.core.cos import COSConfig, get_storage_path


@pytest.mark.unit
@pytest.mark.cos_service
class TestCOSService:
    """COS服务单元测试类"""

    @pytest.fixture
    def mock_cos_config(self):
        """创建mock COS配置"""
        return COSConfig(
            secret_id="test-secret-id",
            secret_key="test-secret-key",
            region="test-region",
            bucket="test-bucket",
            scheme="https",
            endpoint=None
        )

    @pytest.fixture
    def test_file_data(self):
        """测试文件数据"""
        return {
            "filename": "test.jpg",
            "content": b"test file content",
            "content_type": "image/jpeg",
            "user_id": "test-user-123"
        }

    def test_init_with_valid_config(self, mock_cos_config):
        """测试使用有效配置初始化"""
        # 使用patch临时设置配置
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()
            assert service.config is not None
            # COS服务直接访问_client属性
            assert service._client is not None

    def test_init_with_missing_config(self):
        """测试使用缺失配置初始化"""
        # 模拟配置缺失
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=None):
            # 配置缺失会在初始化时抛出异常
            with pytest.raises(AttributeError):
                service = COSStorage()

    def test_init_with_partial_config(self):
        """测试使用部分配置初始化"""
        # 模拟部分配置缺失
        partial_config = COSConfig(
            secret_id="test-secret-id",
            secret_key="",  # 空secret_key
            region="test-region",
            bucket="test-bucket",
            scheme="https"
        )

        with patch('app.core.storage.cos_storage.get_cos_config', return_value=partial_config):
            # 部分配置会在初始化时抛出异常
            with pytest.raises(Exception):
                service = COSStorage()

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_cos_config, test_file_data):
        """测试成功上传文件"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        mock_put_object = MagicMock()
        mock_put_object.return_value = {
            'ETag': '"test-etag-123"',
            'Content-Length': len(test_file_data['content'])
        }
        mock_client.put_object = mock_put_object

        # 替换客户端
        service._client = mock_client

        # 生成COS key - 使用get_storage_path函数
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        cos_key = get_storage_path(service.config, test_file_data['user_id'], date_str, test_file_data['filename'])

        # 执行测试
        result = await service.upload(
            test_file_data['content'],
            cos_key,
            test_file_data['content_type']
        )

        # 验证结果
        assert result.key == cos_key
        assert result.url is not None
        assert result.etag == "test-etag-123"
        assert result.size == len(test_file_data['content'])
        assert result.uploaded_at is not None

        # 验证COS客户端调用
        mock_put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_cos_error(self, mock_cos_config, test_file_data):
        """测试上传文件时COS错误"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端错误
        mock_client = MagicMock()
        mock_put_object = MagicMock()
        mock_put_object.side_effect = Exception("COS upload error")
        mock_client.put_object = mock_put_object

        # 替换客户端
        service._client = mock_client

        # 生成COS key - 使用get_storage_path函数
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        cos_key = get_storage_path(service.config, test_file_data['user_id'], date_str, test_file_data['filename'])

        # 执行测试并验证异常
        with pytest.raises(Exception, match="COS upload error"):
            await service.upload(
                test_file_data['content'],
                cos_key,
                test_file_data['content_type']
            )

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self, mock_cos_config):
        """测试成功生成预签名URL"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        mock_presigned_url = "https://presigned-url.com/test-file.jpg"
        mock_get_presigned_url = MagicMock(return_value=mock_presigned_url)
        mock_client.get_presigned_url = mock_get_presigned_url

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/test-file.jpg"
        operation = "get"
        expires = 3600

        # 执行测试
        result = await service.generate_url(cos_key, expires, operation)

        # 验证结果
        assert result is not None
        mock_get_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_url_invalid_method(self, mock_cos_config):
        """测试使用无效方法生成预签名URL"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/test-file.jpg"
        invalid_operation = "invalid_operation"

        # 执行测试并验证异常
        with pytest.raises(Exception, match="不支持的操作类型"):
            await service.generate_url(cos_key, 3600, invalid_operation)

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_cos_config):
        """测试成功删除文件"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        mock_delete_object = MagicMock()
        mock_delete_object.return_value = None  # 删除成功返回None
        mock_client.delete_object = mock_delete_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/test-file.jpg"

        # 执行测试
        result = await service.delete(cos_key)

        # 验证结果
        assert result is True
        mock_delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, mock_cos_config):
        """测试删除不存在的文件"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端 - 文件不存在错误
        mock_client = MagicMock()
        mock_delete_object = MagicMock()
        mock_delete_object.side_effect = Exception("NoSuchKey: The specified key does not exist")
        mock_client.delete_object = mock_delete_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/non-existent-file.jpg"

        # 执行测试并验证异常
        with pytest.raises(Exception, match="NoSuchKey"):
            await service.delete(cos_key)

    @pytest.mark.asyncio
    async def test_file_exists_success(self, mock_cos_config):
        """测试成功检查文件存在"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        mock_head_object = MagicMock()
        mock_head_object.return_value = {
            'Content-Length': 1024,
            'Content-Type': 'image/jpeg',
            'ETag': 'test-etag'
        }
        mock_client.head_object = mock_head_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/test-file.jpg"

        # 执行测试
        result = await service.exists(cos_key)

        # 验证结果
        assert result is True
        mock_head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_not_found(self, mock_cos_config):
        """测试检查不存在的文件"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端 - 文件不存在
        mock_client = MagicMock()
        mock_head_object = MagicMock()
        mock_head_object.side_effect = Exception("404 Not Found")
        mock_client.head_object = mock_head_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/non-existent-file.jpg"

        # 执行测试
        result = await service.exists(cos_key)

        # 验证结果
        assert result is False
        mock_head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self, mock_cos_config):
        """测试成功获取文件元数据"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端
        mock_client = MagicMock()
        mock_head_object = MagicMock()
        mock_head_object.return_value = {
            'ContentType': 'image/jpeg',
            'ContentLength': 1024,
            'ETag': '"test-etag-123"',
            'LastModified': 'Wed, 01 Jan 2023 00:00:00 GMT',
            'Metadata': {'custom-field': 'custom-value'}
        }
        mock_client.head_object = mock_head_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/test-file.jpg"

        # 执行测试
        result = await service.get_metadata(cos_key)

        # 验证结果
        assert result is not None
        assert result['content_type'] == 'image/jpeg'
        assert result['content_length'] == 1024
        assert result['etag'] == 'test-etag-123'
        assert 'last_modified' in result
        assert 'metadata' in result

    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, mock_cos_config):
        """测试获取不存在的文件的元数据"""
        # 创建服务实例
        with patch('app.core.storage.cos_storage.get_cos_config', return_value=mock_cos_config):
            service = COSStorage()

        # Mock COS客户端 - 文件不存在
        mock_client = MagicMock()
        mock_head_object = MagicMock()
        mock_head_object.side_effect = Exception("404 Not Found")
        mock_client.head_object = mock_head_object

        # 替换客户端
        service._client = mock_client

        # 测试数据
        cos_key = "images/test-user/non-existent-file.jpg"

        # 执行测试并验证异常
        with pytest.raises(Exception, match="404 Not Found"):
            await service.get_metadata(cos_key)

    def test_generate_storage_path(self, mock_cos_config):
        """测试生成存储路径"""
        # 测试数据
        filename = "test-image.jpg"
        user_id = "test-user-123"
        date_str = "20230101"

        # 执行测试
        cos_key = get_storage_path(mock_cos_config, user_id, date_str, filename)

        # 验证结果
        assert cos_key == f"images/test-user-123/20230101/test-image.jpg"

    def test_generate_storage_path_with_user_isolation(self, mock_cos_config):
        """测试用户隔离的存储路径生成"""
        # 测试数据
        filename = "test-image.png"
        user_id = "test-user-456"
        date_str = "20230101"

        # 执行测试
        cos_key = get_storage_path(mock_cos_config, user_id, date_str, filename)

        # 验证结果
        assert cos_key == f"images/test-user-456/20230101/test-image.png"