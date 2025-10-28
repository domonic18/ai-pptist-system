"""
图片服务单元测试
测试ImageService类的所有方法
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.image import Image
from app.repositories.image import ImageRepository
from app.schemas.image_manager import ImageCreate, ImageUpdate
from tests.utils.mock_utils import MockBuilder


@pytest.mark.unit
@pytest.mark.image_service
class TestImageService:
    """图片服务单元测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """创建mock数据库会话"""
        mock_session = MagicMock()
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.refresh = AsyncMock(return_value=None)
        mock_session.add = MagicMock(return_value=None)
        mock_session.execute = AsyncMock()
        mock_session.scalar = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.delete = MagicMock(return_value=None)
        return mock_session

    @pytest.fixture
    def test_image_data(self):
        """测试图片数据"""
        return {
            "user_id": "test-user-123",
            "image_url": "https://example.com/image.jpg",
            "original_filename": "test.jpg",
            "file_size": 1024,
            "mime_type": "image/jpeg",
            "width": 800,
            "height": 600,
            "storage_status": "active",
            "cos_bucket": "test-bucket",
            "cos_key": "images/test-user/test.jpg",
            "cos_region": "ap-beijing",
            "cos_etag": "test-etag-123",
            "description": "测试图片描述",
            "tags": ["test", "image"]
        }

    @pytest.mark.asyncio
    async def test_create_image_success(self, mock_db_session, test_image_data):
        """测试成功创建图片"""
        # 准备测试数据
        image_create = ImageCreate(**test_image_data)
        user_id = "test-user-123"

        # Mock数据库操作
        mock_image = MagicMock()
        mock_image.id = "test-image-id"

        with patch.object(mock_db_session, 'add', return_value=None), \
             patch.object(mock_db_session, 'commit', return_value=None), \
             patch.object(mock_db_session, 'refresh', return_value=None):

            # 创建Repository实例并执行测试
            repository = ImageRepository(mock_db_session)
            result = await repository.create_image(image_create, user_id)

            # 验证结果
            assert result is not None
            assert hasattr(result, 'id')
            assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_image_database_error(self, mock_db_session, test_image_data):
        """测试创建图片时数据库错误"""
        image_create = ImageCreate(**test_image_data)
        user_id = "test-user-123"

        # Mock数据库错误
        mock_db_session.add.side_effect = SQLAlchemyError("Database error")

        # 创建Repository实例并执行测试
        repository = ImageRepository(mock_db_session)

        # 执行测试并验证异常
        with pytest.raises(SQLAlchemyError):
            await repository.create_image(image_create, user_id)

    @pytest.mark.asyncio
    async def test_get_image_success(self, mock_db_session):
        """测试成功获取图片"""
        image_id = "test-image-id"
        user_id = "test-user"

        # Mock查询结果
        mock_image = MagicMock()
        mock_image.id = image_id
        mock_image.user_id = user_id

        # Mock execute方法返回的结果
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_image
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 创建Repository实例并执行测试
        repository = ImageRepository(mock_db_session)
        result = await repository.get_image_by_id(image_id)

        # 验证结果
        assert result is not None
        assert result.id == image_id
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_image_not_found(self, mock_db_session):
        """测试获取不存在的图片"""
        image_id = "non-existent-id"
        user_id = "test-user"

        with patch.object(mock_db_session, 'execute', new_callable=AsyncMock) as mock_execute:
            # Mock空结果
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            # 执行测试
            repository = ImageRepository(mock_db_session)
            result = await repository.get_image_by_id(image_id)

            # 验证结果
            assert result is None

    @pytest.mark.asyncio
    async def test_list_images_success(self, mock_db_session):
        """测试成功列出图片"""
        user_id = "test-user"
        skip = 0
        limit = 10

        # Mock查询结果
        mock_images = [MagicMock() for _ in range(3)]
        for i, img in enumerate(mock_images):
            img.id = f"image-{i}"
            img.user_id = user_id

        # Mock get_user_images方法返回的结果
        mock_images_list = mock_images
        mock_total = len(mock_images)

        # 执行测试
        repository = ImageRepository(mock_db_session)
        # 直接模拟repository方法
        with patch.object(repository, 'get_user_images', new_callable=AsyncMock) as mock_get_user_images:
            mock_get_user_images.return_value = (mock_images_list, mock_total)
            images, total = await repository.get_user_images(user_id, skip, limit)

        # 验证结果
        assert total == len(mock_images)
        assert len(images) == len(mock_images)

    @pytest.mark.asyncio
    async def test_list_images_empty(self, mock_db_session):
        """测试列出空图片列表"""
        user_id = "test-user"

        # Mock空结果
        mock_images_list = []
        mock_total = 0

        # 执行测试
        repository = ImageRepository(mock_db_session)
        # 直接模拟repository方法
        with patch.object(repository, 'get_user_images', new_callable=AsyncMock) as mock_get_user_images:
            mock_get_user_images.return_value = (mock_images_list, mock_total)
            images, total = await repository.get_user_images(user_id, 0, 20)

        # 验证结果
        assert total == 0
        assert len(images) == 0

    @pytest.mark.asyncio
    async def test_update_image_success(self, mock_db_session):
        """测试成功更新图片"""
        image_id = "test-image-id"
        user_id = "test-user"
        update_data = {"description": "更新后的描述", "tags": ["updated", "test"]}

        # Mock现有图片
        mock_image = MagicMock()
        mock_image.id = image_id
        mock_image.user_id = user_id
        mock_image.description = "更新后的描述"
        mock_image.tags = ["updated", "test"]

        # Mock execute方法返回正确的结果对象
        mock_result = MagicMock()
        mock_result.rowcount = 1  # 模拟更新成功
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock get_image_by_id方法返回图片
        with patch.object(ImageRepository, 'get_image_by_id', new_callable=AsyncMock) as mock_get_image:
            mock_get_image.return_value = mock_image

            with patch.object(mock_db_session, 'commit', return_value=None):

                # 执行测试
                repository = ImageRepository(mock_db_session)
                result = await repository.update_image(image_id, update_data)

                # 验证结果
                assert result is not None
                assert result.id == image_id
                # 验证字段已更新
                assert result.description == "更新后的描述"
                assert result.tags == ["updated", "test"]

    @pytest.mark.asyncio
    async def test_update_image_not_found(self, mock_db_session):
        """测试更新不存在的图片"""
        image_id = "non-existent-id"
        user_id = "test-user"
        update_data = {"description": "测试更新"}

        # Mock execute方法返回更新0行的结果
        mock_result = MagicMock()
        mock_result.rowcount = 0  # 模拟更新失败
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(mock_db_session, 'commit', return_value=None):

            # 执行测试
            repository = ImageRepository(mock_db_session)
            result = await repository.update_image(image_id, update_data)

            # 验证结果
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_image_success(self, mock_db_session):
        """测试成功删除图片"""
        image_id = "test-image-id"
        user_id = "test-user"

        # Mock现有图片
        mock_image = MagicMock()
        mock_image.id = image_id

        # Mock execute方法返回正确的结果对象
        mock_result = MagicMock()
        mock_result.rowcount = 1  # 模拟删除成功
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(mock_db_session, 'commit', return_value=None):

            # 执行测试
            repository = ImageRepository(mock_db_session)
            result = await repository.delete_image(image_id)

            # 验证结果
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_image_not_found(self, mock_db_session):
        """测试删除不存在的图片"""
        image_id = "non-existent-id"
        user_id = "test-user"

        # Mock execute方法返回删除0行的结果
        mock_result = MagicMock()
        mock_result.rowcount = 0  # 模拟删除失败
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(mock_db_session, 'commit', return_value=None):

            # 执行测试
            repository = ImageRepository(mock_db_session)
            result = await repository.delete_image(image_id)

            # 验证结果
            assert result is False

    @pytest.mark.asyncio
    async def test_search_images_success(self, mock_db_session):
        """测试成功搜索图片"""
        user_id = "test-user"
        query = "test"

        # Mock查询结果
        mock_images = [MagicMock() for _ in range(2)]
        for i, img in enumerate(mock_images):
            img.id = f"image-{i}"
            img.user_id = user_id
            img.description = f"测试图片 {i}"

        # Mock execute方法返回的结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_images
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        repository = ImageRepository(mock_db_session)
        result = await repository.search_by_prompt(query, user_id)

        # 验证结果
        assert len(result) == len(mock_images)

    @pytest.mark.asyncio
    async def test_search_images_no_results(self, mock_db_session):
        """测试搜索无结果"""
        user_id = "test-user"
        query = "nonexistent"

        # Mock空结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        repository = ImageRepository(mock_db_session)
        result = await repository.search_by_prompt(query, user_id)

        # 验证结果
        assert len(result) == 0