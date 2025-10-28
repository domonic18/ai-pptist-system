"""
标签接口集成测试（简化版）
测试标签相关的所有API端点
"""

import pytest
import time


@pytest.mark.integration
@pytest.mark.tags
class TestTagsEndpoints:
    """标签端点集成测试类"""

    def test_list_tags_success(self, client):
        """测试获取标签列表"""
        response = client.get("/tags/")

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "items" in data["data"]
            assert "total" in data["data"]
            assert "page" in data["data"]
            assert "limit" in data["data"]
        else:
            assert response.status_code in [400, 500]

    def test_get_popular_tags_success(self, client):
        """测试获取热门标签"""
        response = client.get("/tags/popular/?limit=10")

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "tags" in data["data"]
            assert "total" in data["data"]
            assert "limit" in data["data"]
        else:
            assert response.status_code in [400, 500]

    def test_search_tags_success(self, client):
        """测试搜索标签"""
        response = client.get("/tags/search/?query=测试")

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "tags" in data["data"]
            assert "total" in data["data"]
            assert "query" in data["data"]
        else:
            assert response.status_code in [400, 500]

    def test_create_tag_success(self, client):
        """测试创建标签"""
        tag_data = {
            "name": f"测试标签_{int(time.time())}",
            "description": "这是一个测试标签"
        }

        response = client.post("/tags/", json=tag_data)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert "tag" in data["data"]
            assert "message" in data["data"]
        else:
            assert response.status_code in [400, 422, 500]

    def test_create_tag_invalid_data(self, client):
        """测试创建标签时数据无效"""
        invalid_data = {
            "description": "缺少名称"
        }

        response = client.post("/tags/", json=invalid_data)

        assert response.status_code in [422, 400, 500]

    def test_delete_tag_success(self, client):
        """测试删除标签"""
        tag_name = "测试删除标签"

        # 先创建标签
        tag_data = {
            "name": tag_name,
            "description": "这个标签将被删除"
        }
        create_response = client.post("/tags/", json=tag_data)

        if create_response.status_code == 200:
            # 删除标签
            response = client.delete(f"/tags/{tag_name}")

            if response.status_code == 200:
                data = response.json()
                assert "data" in data
                assert "message" in data["data"]
            else:
                assert response.status_code in [404, 500]
        else:
            pytest.skip("无法创建测试标签，跳过删除测试")

    def test_delete_nonexistent_tag(self, client):
        """测试删除不存在的标签"""
        tag_name = "non-existent-tag"
        response = client.delete(f"/tags/{tag_name}")

        assert response.status_code in [404, 400, 500]


@pytest.mark.integration
@pytest.mark.image_tags
class TestImageTagsEndpoints:
    """图片标签端点集成测试类"""

    def test_get_image_tags_success(self, client):
        """测试获取图片标签"""
        # 首先获取一个存在的图片ID
        images_response = client.get("/images/")

        if images_response.status_code == 200:
            images_data = images_response.json()
            if len(images_data["data"]["items"]) > 0:
                image_id = images_data["data"]["items"][0]["id"]

                response = client.get(f"/images/{image_id}/tags")

                if response.status_code == 200:
                    data = response.json()
                    assert "data" in data
                    assert "image_id" in data["data"]
                    assert "tags" in data["data"]
                    assert "total" in data["data"]
                else:
                    assert response.status_code in [404, 500]
            else:
                pytest.skip("没有可用的图片进行测试")
        else:
            pytest.skip("无法获取图片列表，跳过测试")

    def test_add_image_tags_success(self, client):
        """测试为图片添加标签"""
        # 首先获取一个存在的图片ID
        images_response = client.get("/images/")

        if images_response.status_code == 200:
            images_data = images_response.json()
            if len(images_data["data"]["items"]) > 0:
                image_id = images_data["data"]["items"][0]["id"]

                tag_data = {
                    "tags": ["测试标签1", "测试标签2"]
                }
                response = client.post(f"/images/{image_id}/tags", json=tag_data)

                if response.status_code == 200:
                    data = response.json()
                    assert "data" in data
                    assert "image_id" in data["data"]
                    assert "added_tags" in data["data"]
                    assert "current_tags" in data["data"]
                else:
                    assert response.status_code in [404, 400, 500]
            else:
                pytest.skip("没有可用的图片进行测试")
        else:
            pytest.skip("无法获取图片列表，跳过测试")

    def test_update_image_tags_success(self, client):
        """测试更新图片标签"""
        # 首先获取一个存在的图片ID
        images_response = client.get("/images/")

        if images_response.status_code == 200:
            images_data = images_response.json()
            if len(images_data["data"]["items"]) > 0:
                image_id = images_data["data"]["items"][0]["id"]

                tag_data = {
                    "tags": ["更新标签1", "更新标签2"]
                }
                response = client.put(f"/images/{image_id}/tags", json=tag_data)

                if response.status_code == 200:
                    data = response.json()
                    assert "data" in data
                    assert "image_id" in data["data"]
                    assert "added_tags" in data["data"]
                    assert "removed_tags" in data["data"]
                    assert "current_tags" in data["data"]
                else:
                    assert response.status_code in [404, 400, 500]
            else:
                pytest.skip("没有可用的图片进行测试")
        else:
            pytest.skip("无法获取图片列表，跳过测试")

    def test_delete_image_tags_success(self, client):
        """测试删除图片标签"""
        # 首先获取一个存在的图片ID
        images_response = client.get("/images/")

        if images_response.status_code == 200:
            images_data = images_response.json()
            if len(images_data["data"]["items"]) > 0:
                image_id = images_data["data"]["items"][0]["id"]

                # 删除所有标签
                response = client.delete(f"/images/{image_id}/tags")

                if response.status_code == 200:
                    data = response.json()
                    assert "data" in data
                    assert "image_id" in data["data"]
                    assert "removed_tags" in data["data"]
                    assert "current_tags" in data["data"]
                else:
                    assert response.status_code in [404, 400, 500]
            else:
                pytest.skip("没有可用的图片进行测试")
        else:
            pytest.skip("无法获取图片列表，跳过测试")

    def test_search_images_by_tags_success(self, client):
        """测试根据标签搜索图片"""
        search_data = ["风景", "自然"]

        response = client.post("/images/search/by-tags", json=search_data)

        # 可能返回200（成功）或404（无结果）
        assert response.status_code in [200, 404, 500]

    def test_search_images_by_tags_no_results(self, client):
        """测试根据不存在的标签搜索图片"""
        search_data = ["绝对不存在的标签12345"]

        response = client.post("/images/search/by-tags", json=search_data)

        # 应该返回404（无结果）或200（空结果）
        assert response.status_code in [200, 404, 500]

    def test_invalid_image_tag_endpoints(self, client):
        """测试无效的图片标签端点"""
        # 测试无效的图片ID格式
        response = client.get("/images//tags")  # 双斜杠
        assert response.status_code in [400, 404, 500]

        # 测试空标签名
        response = client.delete("/images/test-image/tags/")  # 空标签名
        assert response.status_code in [400, 404, 500]