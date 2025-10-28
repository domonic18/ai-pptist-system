"""
标签服务单元测试
测试TagService类的所有方法
遵循项目测试规范：快速执行，无外部依赖
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.tag_service import TagService
from app.schemas.tag import TagCreate, ImageTagAdd, ImageTagUpdate, TagSearchParams


@pytest.mark.unit
@pytest.mark.tag_service
class TestTagService:
    """标签服务单元测试类"""

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
    def mock_image_repo(self):
        """创建mock图片仓库"""
        mock_repo = MagicMock()
        mock_repo.get_image_by_id = AsyncMock()
        mock_repo.update_image = AsyncMock()
        mock_repo.get_user_images = AsyncMock()
        return mock_repo

    @pytest.fixture
    def mock_tag_repo(self):
        """创建mock标签仓库"""
        mock_repo = MagicMock()
        mock_repo.get_tag_by_name = AsyncMock()
        mock_repo.create_tag = AsyncMock()
        mock_repo.create_or_get_tags = AsyncMock()
        mock_repo.increment_tag_usage = AsyncMock()
        mock_repo.decrement_tag_usage = AsyncMock()
        mock_repo.get_all_tags = AsyncMock()
        mock_repo.get_popular_tags = AsyncMock()
        mock_repo.delete_tag_by_name = AsyncMock()
        return mock_repo

    @pytest.fixture
    def test_image(self):
        """测试图片对象"""
        mock_image = MagicMock()
        mock_image.id = "test-image-123"
        mock_image.user_id = "test-user-123"
        mock_image.tags = ["风景", "自然"]
        return mock_image

    @pytest.fixture
    def test_tag(self):
        """测试标签对象"""
        mock_tag = MagicMock()
        mock_tag.id = "test-tag-123"
        mock_tag.name = "新标签"
        mock_tag.description = "新标签描述"
        mock_tag.usage_count = 5
        mock_tag.to_dict.return_value = {
            "id": mock_tag.id,
            "name": mock_tag.name,
            "description": mock_tag.description,
            "usage_count": mock_tag.usage_count
        }
        return mock_tag

    @pytest.mark.asyncio
    async def test_get_image_tags_success(self, mock_db_session, mock_image_repo, test_image):
        """测试成功获取图片标签"""
        # 准备测试数据
        image_id = "test-image-123"
        user_id = "test-user-123"

        # Mock图片存在
        mock_image_repo.get_image_by_id.return_value = test_image

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo):

            service = TagService(mock_db_session)
            result = await service.get_image_tags(image_id, user_id)

            # 验证结果
            assert result is not None
            assert result["image_id"] == image_id
            assert result["tags"] == test_image.tags
            assert result["total"] == len(test_image.tags)

    @pytest.mark.asyncio
    async def test_get_image_tags_not_found(self, mock_db_session, mock_image_repo):
        """测试获取不存在图片的标签"""
        # 准备测试数据
        image_id = "non-existent-id"
        user_id = "test-user-123"

        # Mock图片不存在
        mock_image_repo.get_image_by_id.return_value = None

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo):

            service = TagService(mock_db_session)

            # 执行测试并验证异常
            with pytest.raises(ValueError, match="图片不存在"):
                await service.get_image_tags(image_id, user_id)

    @pytest.mark.asyncio
    async def test_get_image_tags_permission_denied(self, mock_db_session, mock_image_repo, test_image):
        """测试获取无权限图片的标签"""
        # 准备测试数据
        image_id = "test-image-123"
        user_id = "other_user"  # 不同的用户

        # Mock图片存在但属于其他用户
        mock_image_repo.get_image_by_id.return_value = test_image

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo):

            service = TagService(mock_db_session)

            # 执行测试并验证异常
            with pytest.raises(ValueError, match="无权访问该图片"):
                await service.get_image_tags(image_id, user_id)

    @pytest.mark.asyncio
    async def test_add_image_tags_success(self, mock_db_session, mock_image_repo, mock_tag_repo, test_image):
        """测试成功添加图片标签"""
        # 准备测试数据
        image_id = "test-image-123"
        user_id = "test-user-123"
        tag_data = ImageTagAdd(tags=["新标签"])

        # Mock图片存在
        mock_image_repo.get_image_by_id.return_value = test_image

        # Mock更新后的图片
        updated_image = MagicMock()
        updated_image.tags = ["风景", "自然", "新标签"]
        mock_image_repo.update_image.return_value = updated_image

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo), \
             patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.add_image_tags(image_id, user_id, tag_data)

            # 验证结果
            assert result is not None
            assert result["image_id"] == image_id
            assert "新标签" in result["added_tags"]
            assert "新标签" in result["current_tags"]

    @pytest.mark.asyncio
    async def test_create_tag_success(self, mock_db_session, mock_tag_repo, test_tag):
        """测试成功创建标签"""
        # 准备测试数据
        tag_data = TagCreate(name="新标签", description="新标签描述")

        # Mock标签不存在
        mock_tag_repo.get_tag_by_name.return_value = None
        mock_tag_repo.create_tag.return_value = test_tag

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.create_tag(tag_data)

            # 验证结果
            assert result is not None
            assert "tag" in result
            assert "message" in result
            assert result["tag"]["name"] == tag_data.name

    @pytest.mark.asyncio
    async def test_create_tag_already_exists(self, mock_db_session, mock_tag_repo, test_tag):
        """测试创建已存在的标签"""
        # 准备测试数据
        tag_data = TagCreate(name="已存在标签", description="标签描述")

        # Mock标签已存在
        mock_tag_repo.get_tag_by_name.return_value = test_tag

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)

            # 执行测试并验证异常
            with pytest.raises(ValueError, match="标签 '已存在标签' 已存在"):
                await service.create_tag(tag_data)

    @pytest.mark.asyncio
    async def test_delete_tag_success(self, mock_db_session, mock_tag_repo, test_tag):
        """测试成功删除标签"""
        # 准备测试数据
        tag_name = "测试标签"

        # Mock标签存在
        mock_tag_repo.get_tag_by_name.return_value = test_tag
        mock_tag_repo.delete_tag_by_name.return_value = True

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.delete_tag(tag_name)

            # 验证结果
            assert result is not None
            assert "message" in result
            assert "deleted_tag" in result
            assert result["deleted_tag"] == tag_name

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, mock_db_session, mock_tag_repo):
        """测试删除不存在的标签"""
        # 准备测试数据
        tag_name = "不存在标签"

        # Mock标签不存在
        mock_tag_repo.get_tag_by_name.return_value = None

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)

            # 执行测试并验证异常
            with pytest.raises(ValueError, match="标签 '不存在标签' 不存在"):
                await service.delete_tag(tag_name)

    @pytest.mark.asyncio
    async def test_get_all_tags_success(self, mock_db_session, mock_tag_repo, test_tag):
        """测试成功获取所有标签"""
        # 准备测试数据
        search_params = TagSearchParams(
            page=1,
            limit=20,
            sort_by="usage_count",
            sort_order="desc"
        )

        # Mock标签Repository
        mock_tag_repo.get_all_tags.return_value = ([test_tag], 1)

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.get_all_tags(search_params)

            # 验证结果
            assert result is not None
            assert "items" in result
            assert "total" in result
            assert "page" in result
            assert "limit" in result
            assert "total_pages" in result
            assert len(result["items"]) == 1
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_popular_tags_success(self, mock_db_session, mock_tag_repo, test_tag):
        """测试成功获取热门标签"""
        # 准备测试数据
        limit = 10

        # Mock标签Repository
        mock_tag_repo.get_popular_tags.return_value = [test_tag]

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.get_popular_tags(limit)

            # 验证结果
            assert result is not None
            assert "tags" in result
            assert "total" in result
            assert "limit" in result
            assert len(result["tags"]) == 1
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_tags_success(self, mock_db_session, mock_tag_repo, test_tag):
        """测试成功搜索标签"""
        # 准备测试数据
        query = "测试"
        limit = 10

        # Mock标签Repository
        mock_tag_repo.get_all_tags.return_value = ([test_tag], 1)

        # 创建TagService实例
        with patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.search_tags(query, limit)

            # 验证结果
            assert result is not None
            assert "tags" in result
            assert "total" in result
            assert "query" in result
            assert result["limit"] == limit
            assert len(result["tags"]) == 1
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_search_images_by_tags_success(self, mock_db_session, mock_image_repo, test_image):
        """测试成功根据标签搜索图片"""
        # 准备测试数据
        user_id = "test-user-123"
        tags = ["风景"]
        skip = 0
        limit = 20

        # Mock用户图片列表
        mock_images = [test_image]
        mock_total = 1
        mock_image_repo.get_user_images.return_value = (mock_images, mock_total)

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo):

            service = TagService(mock_db_session)
            result = await service.search_images_by_tags(user_id, tags, skip, limit)

            # 验证结果
            assert result is not None
            assert "items" in result
            assert "total" in result
            assert "skip" in result
            assert "limit" in result
            assert "query_tags" in result
            assert len(result["items"]) == 1
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_update_image_tags_success(self, mock_db_session, mock_image_repo, mock_tag_repo, test_image):
        """测试成功更新图片标签"""
        # 准备测试数据
        image_id = "test-image-123"
        user_id = "test-user-123"
        tag_data = ImageTagUpdate(tags=["建筑", "城市"])

        # Mock图片存在
        mock_image_repo.get_image_by_id.return_value = test_image

        # Mock更新后的图片
        updated_image = MagicMock()
        updated_image.tags = ["建筑", "城市"]
        mock_image_repo.update_image.return_value = updated_image

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo), \
             patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.update_image_tags(image_id, user_id, tag_data)

            # 验证结果
            assert result is not None
            assert result["image_id"] == image_id
            assert set(result["added_tags"]) == {"建筑", "城市"}
            assert set(result["removed_tags"]) == {"风景", "自然"}
            assert result["current_tags"] == ["建筑", "城市"]
            assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_delete_image_tags_success(self, mock_db_session, mock_image_repo, mock_tag_repo, test_image):
        """测试成功删除图片标签"""
        # 准备测试数据
        image_id = "test-image-123"
        user_id = "test-user-123"
        tags_to_delete = ["风景"]

        # Mock图片存在
        mock_image_repo.get_image_by_id.return_value = test_image

        # Mock更新后的图片
        updated_image = MagicMock()
        updated_image.tags = ["自然"]
        mock_image_repo.update_image.return_value = updated_image

        # 创建TagService实例
        with patch('app.services.image.tag_service.ImageRepository', return_value=mock_image_repo), \
             patch('app.services.image.tag_service.TagRepository', return_value=mock_tag_repo):

            service = TagService(mock_db_session)
            result = await service.delete_image_tags(image_id, user_id, tags_to_delete)

            # 验证结果
            assert result is not None
            assert result["image_id"] == image_id
            assert result["removed_tags"] == ["风景"]
            assert result["current_tags"] == ["自然"]
            assert result["total"] == 1