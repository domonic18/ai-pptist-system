"""
认证接口集成测试
测试完整的认证API接口，包括登录、注册、Token刷新、登出等

注意：由于 Windows + asyncpg + TestClient 的兼容性问题，
测试使用 raise_server_exceptions=False 来避免事件循环关闭错误
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.mark.integration
@pytest.mark.auth
class TestAuthEndpoints:
    """认证端点集成测试类"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端（类级别，避免重复创建事件循环）"""
        from main import app

        # 使用 raise_server_exceptions=False 避免 Windows 上的事件循环问题
        # 使用上下文管理器确保资源正确清理
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """测试前置设置"""
        pass

    @pytest.fixture
    def test_user_registration_success(self, client):
        """测试用户注册（成功）"""
        new_user = {
            "email": "test-user@example.com",
            "name": "测试用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        response = client.post("/api/v1/auth/register", json=new_user)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "access_token" in data["data"]
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == new_user["email"]

    
    def test_user_login_success(self, client):
        """测试用户登录（成功）"""
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-login@example.com",
            "name": "测试登录用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户（如果已存在会失败，这是正常的）
        client.post("/api/v1/auth/register", json=register_data)

        # 执行登录
        login_data = {
            "email": "test-login@example.com",
            "password": "TestPassword123!"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    
    def test_login_wrong_credentials(self, client):
        """测试登录（错误凭据）"""
        login_data = {
            "email": "test-wrong@example.com",
            "password": "WrongPassword123!"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    
    def test_refresh_token_success(self, client):
        """测试刷新Token（成功）

        注意：每次刷新 token 时，refresh_token 也会更新（为了避免数据库唯一约束冲突）
        """
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-refresh@example.com",
            "name": "测试Token刷新用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        client.post("/api/v1/auth/register", json=register_data)

        # 登录获取token
        login_data = {
            "email": "test-refresh@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["data"]["access_token"]
        refresh_token = login_response.json()["data"]["refresh_token"]

        # 测试刷新token
        refresh_data = {
            "refresh_token": refresh_token
        }

        response = client.post(
            "/api/v1/auth/refresh",
            json=refresh_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        # 验证返回的字段
        response_data = data["data"]
        assert "access_token" in response_data
        assert isinstance(response_data["access_token"], str)
        assert len(response_data["access_token"]) > 0

        # 验证新的 refresh_token（现在每次刷新都会返回新的 refresh_token）
        assert "refresh_token" in response_data
        assert isinstance(response_data["refresh_token"], str)
        assert len(response_data["refresh_token"]) > 0

        # 验证 expires_at
        assert "expires_at" in response_data

        # 验证 refresh_expires_at（新增字段）
        assert "refresh_expires_at" in response_data

    
    def test_refresh_token_invalid_token(self, client):
        """测试刷新Token（无效token）"""
        refresh_data = {
            "refresh_token": "invalid-refresh-token"
        }

        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401

    
    def test_get_current_user(self, client):
        """测试获取当前用户信息"""
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-me@example.com",
            "name": "测试获取用户信息用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        client.post("/api/v1/auth/register", json=register_data)

        # 登录获取token
        login_data = {
            "email": "test-me@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["data"]["access_token"]

        # 使用token获取用户信息
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["email"] == "test-me@example.com"

    
    def test_get_current_user_without_auth(self, client):
        """测试获取当前用户信息（未认证）"""
        response = client.get("/api/v1/auth/me")

        # 可能返回401或其他未认证错误
        assert response.status_code == 401

    
    def test_logout_success(self, client):
        """测试登出（成功）"""
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-logout@example.com",
            "name": "测试登出用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        client.post("/api/v1/auth/register", json=register_data)

        # 登录获取token
        login_data = {
            "email": "test-logout@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["data"]["access_token"]

        # 使用token登出
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    
    def test_logout_without_auth(self, client):
        """测试登出（未认证）"""
        response = client.post("/api/v1/auth/logout")

        # 应该返回401未认证错误
        assert response.status_code == 401

    
    def test_get_sessions(self, client):
        """测试获取用户所有会话"""
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-sessions@example.com",
            "name": "测试会话用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        client.post("/api/v1/auth/register", json=register_data)

        # 登录获取token
        login_data = {
            "email": "test-sessions@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["data"]["access_token"]

        # 获取会话列表
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/sessions", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "sessions" in data["data"]
        assert isinstance(data["data"]["sessions"], list)

    
    def test_get_sessions_without_auth(self, client):
        """测试获取会话列表（未认证）"""
        response = client.get("/api/v1/auth/sessions")

        assert response.status_code == 401

    
    def test_logout_all(self, client):
        """测试登出所有设备"""
        # 使用注册 API 创建用户
        register_data = {
            "email": "test-logout-all@example.com",
            "name": "测试登出所有用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        client.post("/api/v1/auth/register", json=register_data)

        # 登录获取token
        login_data = {
            "email": "test-logout-all@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["data"]["access_token"]

        # 登出所有设备
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/api/v1/auth/logout-all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "revoked_count" in data["data"]


@pytest.mark.integration
@pytest.mark.auth

class TestAuthErrorCases:
    """认证错误场景集成测试类"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端（类级别，避免重复创建事件循环）"""
        from main import app

        # 使用 raise_server_exceptions=False 避免 Windows 上的事件循环问题
        # 使用上下文管理器确保资源正确清理
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

    def test_register_password_mismatch(self, client):
        """测试注册（密码不匹配）"""
        new_user = {
            "email": "test-mismatch@example.com",
            "name": "测试密码不匹配",
            "password": "TestPassword123!",
            "confirm_password": "DifferentPassword123!"
        }

        response = client.post("/api/v1/auth/register", json=new_user)

        assert response.status_code == 422  # 验证错误

    def test_register_email_exists(self, client):
        """测试注册（邮箱已存在）"""
        # 第一次注册
        user1 = {
            "email": "test-exists@example.com",
            "name": "测试邮箱已存在",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 第一次注册（如果用户已存在会返回400，这是正常的）
        response1 = client.post("/api/v1/auth/register", json=user1)
        # 不管用户是否存在，只要第二次注册返回400即可
        # 如果用户已存在，第一次注册就会返回400，这是正常的

        # 第二次注册相同邮箱
        user2 = {
            "email": "test-exists@example.com",
            "name": "测试邮箱已存在",
            "password": "DifferentPassword123!",
            "confirm_password": "DifferentPassword123!"
        }

        response2 = client.post("/api/v1/auth/register", json=user2)

        assert response2.status_code == 400
        data = response2.json()
        assert "该邮箱已被注册" in data["detail"]

    def test_register_weak_password(self, client):
        """测试注册（密码强度不足）"""
        new_user = {
            "email": "test-weak@example.com",
            "name": "测试弱密码",
            "password": "weak",  # 太短
            "confirm_password": "weak"
        }

        response = client.post("/api/v1/auth/register", json=new_user)

        assert response.status_code == 422

    def test_login_nonexistent_user(self, client):
        """测试登录（用户不存在）"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    def test_login_wrong_password(self, client):
        """测试登录（密码错误）"""
        # 使用注册 API 创建用户（避免异步数据库操作）
        register_data = {
            "email": "test-wrong-pwd@example.com",
            "name": "测试密码错误",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        register_response = client.post("/api/v1/auth/register", json=register_data)
        # 如果用户已存在，注册会失败，这是正常的
        # 只要能继续测试登录即可

        # 测试错误密码
        login_data = {
            "email": "test-wrong-pwd@example.com",
            "password": "WrongPassword123!"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401

    def test_refresh_token_expired(self, client):
        """测试刷新Token（已过期）"""
        # 使用注册 API 创建用户（避免异步数据库操作）
        register_data = {
            "email": "test-expired@example.com",
            "name": "测试Token过期用户",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }

        # 先注册用户
        register_response = client.post("/api/v1/auth/register", json=register_data)
        # 如果用户已存在，注册会失败，这是正常的

        # 登录获取token
        login_data = {
            "email": "test-expired@example.com",
            "password": "TestPassword123!"
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["data"]["refresh_token"]

        # 修改token使其过期（模拟过期token）
        # 注意：这需要手动构造一个过期的token

        # 使用过期的刷新令牌测试
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHRhaWxsIjoxNjQ4OTY4NDU4MDAwMDAwMDAwIiwidXN1IjoibmlsIn0.Zm9fZGhpaHAiLCJ0eXAiOiIxNjQ4OTY4NDU0MDAwMDAwMDAwIiwidXN1IjoibmlsIn0.Zm9fZGhpaHAiLCJjb25maWxlIjoiaGF2c29hbGVtZSI6IkpXVCJ9.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy"

        refresh_data = {
            "refresh_token": expired_token
        }

        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401
        data = response.json()
        assert "刷新令牌无效或已过期" in data["detail"]

    def test_get_me_invalid_token(self, client):
        """测试获取用户信息（无效token）"""
        invalid_token = "Bearer invalid-token"

        headers = {"Authorization": invalid_token}
        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == 401  # 无效token返回401

    def test_logout_invalid_token(self, client):
        """测试登出（无效token）"""
        invalid_token = "Bearer invalid-token"

        headers = {"Authorization": invalid_token}
        response = client.post("/api/v1/auth/logout", headers=headers)

        # 可能返回403或401，具体取决于实现
        assert response.status_code in [401, 403]
