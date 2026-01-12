"""
认证服务单元测试
测试JWT Handler、密码Handler和AuthService的核心逻辑
遵循项目测试规范：快速执行，无外部依赖
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.jwt_handler import JWTHandler, jwt_handler
from app.core.auth.password_handler import PasswordHandler, password_handler
from app.services.auth.auth_service import AuthService
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.core.config import settings


@pytest.mark.unit
@pytest.mark.auth
class TestJWTHandler:
    """JWT Handler单元测试类"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "test-user-123"
        additional_claims = {"email": "test@example.com"}

        access_token, jti, expires_at = jwt_handler.create_access_token(
            {"sub": user_id, **additional_claims}
        )

        assert access_token is not None
        assert jti is not None
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.utcnow()

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "test-user-123"

        refresh_token, jti, expires_at = jwt_handler.create_refresh_token(
            {"sub": user_id}
        )

        assert refresh_token is not None
        assert jti is not None
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.utcnow()

    def test_create_token_pair(self):
        """测试创建令牌对"""
        user_id = "test-user-123"
        additional_claims = {"email": "test@example.com"}

        token_data = jwt_handler.create_token_pair(user_id, additional_claims)

        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert "access_jti" in token_data
        assert "refresh_jti" in token_data
        assert token_data["expires_at"] > datetime.utcnow()
        assert token_data["refresh_expires_at"] > datetime.utcnow()

    def test_decode_token(self):
        """测试解码Token"""
        user_id = "test-user-123"

        token, _, _ = jwt_handler.create_access_token({"sub": user_id})

        payload = jwt_handler.decode_token(token)

        assert payload["sub"] == user_id

    def test_verify_access_token_success(self):
        """测试验证访问令牌（成功）"""
        user_id = "test-user-123"

        token, _, _ = jwt_handler.create_access_token({"sub": user_id})

        payload = jwt_handler.verify_access_token(token)

        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_verify_access_token_invalid_type(self):
        """测试验证访问令牌（类型错误）"""
        user_id = "test-user-123"

        _, _, _ = jwt_handler.create_refresh_token({"sub": user_id})

        with pytest.raises(Exception) as exc_info:
            jwt_handler.verify_access_token(_)

    def test_get_token_jti(self):
        """测试从Token获取JTI"""
        user_id = "test-user-123"

        token, jti, _ = jwt_handler.create_access_token({"sub": user_id})

        extracted_jti = jwt_handler.get_token_jti(token)

        assert extracted_jti == jti

    def test_get_user_id_from_token(self):
        """测试从Token获取用户ID"""
        user_id = "test-user-123"

        token, _, _ = jwt_handler.create_access_token({"sub": user_id})

        extracted_user_id = jwt_handler.get_user_id_from_token(token)

        assert extracted_user_id == user_id


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordHandler:
    """密码Handler单元测试类"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "TestPassword123!"

        hashed = password_handler.hash_password(password)

        assert hashed != password
        assert password_handler.verify_password(password, hashed) is True

    def test_verify_password_success(self):
        """测试验证密码（成功）"""
        password = "TestPassword123!"
        hashed = password_handler.hash_password(password)

        is_valid = password_handler.verify_password(password, hashed)

        assert is_valid is True

    def test_verify_password_failure(self):
        """测试验证密码（失败）"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"

        hashed = password_handler.hash_password(password)

        is_valid = password_handler.verify_password(wrong_password, hashed)

        assert is_valid is False

    def test_validate_password_strength_success(self):
        """测试验证密码强度（成功）"""
        # 满足所有要求的密码
        password = "TestPassword123!"

        is_valid, error = password_handler.validate_password_strength(password, raise_error=False)

        assert is_valid is True
        assert error is None

    def test_validate_password_strength_failure(self):
        """测试验证密码强度（失败）"""
        # 不满足大小写字母要求的密码
        password = "testpassword123"
        is_valid, error = password_handler.validate_password_strength(password, raise_error=False)

        assert is_valid is False
        assert "大写字母" in error

    def test_get_password_strength_score(self):
        """测试获取密码强度评分"""
        password = "TestPassword123!"  # 满足所有要求的密码

        score_data = password_handler.get_password_strength_score(password)

        assert "score" in score_data
        assert "strength" in score_data
        assert score_data["score"] >= 60  # 中等强度以上

    def test_generate_random_password(self):
        """测试生成随机密码"""
        password = password_handler.generate_random_password(16)

        assert len(password) == 16
        # 验证生成的密码符合强度要求
        is_valid, _ = password_handler.validate_password_strength(password)
        assert is_valid is True


@pytest.mark.unit
@pytest.mark.auth
class TestAuthService:
    """认证服务单元测试类"""

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
        mock_session.scalars = AsyncMock()
        mock_session.first = AsyncMock()
        return mock_session

    @pytest.fixture
    def mock_repositories(self):
        """创建所有认证相关的mock repository"""
        mock_user_repo = MagicMock()
        mock_session_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        # 配置用户相关方法
        mock_user_repo.authenticate_by_password = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock()

        # 配置会话相关方法
        mock_session_repo.create_session = AsyncMock()
        mock_session_repo.get_by_token_jti = AsyncMock()
        mock_session_repo.revoke_by_token_jti = AsyncMock()

        # 配置登录历史相关方法
        mock_login_history_repo.create_login_record = AsyncMock()

        return {
            "user_repo": mock_user_repo,
            "session_repo": mock_session_repo,
            "login_history_repo": mock_login_history_repo
        }

    @pytest.fixture
    def mock_user(self):
        """创建mock用户对象"""
        user = MagicMock()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.name = "测试用户"
        user.role = "USER"
        user.is_active = True
        user.is_superuser = False
        user.auth_type = "password"
        user.to_dict.return_value = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "auth_type": user.auth_type
        }
        return user

    @pytest.mark.asyncio
    async def test_authenticate_by_password_success(self, mock_db_session, mock_repositories, mock_user):
        """测试密码认证（成功）"""
        email = "test@example.com"
        password = "TestPassword123!"

        # 配置mock返回值
        mock_repositories["user_repo"].authenticate_by_password.return_value = mock_user
        mock_repositories["login_history_repo"].create_login_record = AsyncMock()

        # 创建服务实例
        service = AuthService(mock_db_session)
        # 注入mock repositories
        service.user_repo = mock_repositories["user_repo"]
        service.session_repo = mock_repositories["session_repo"]
        service.login_history_repo = mock_repositories["login_history_repo"]

        # 执行认证
        result = await service.authenticate_by_password(
            email=email,
            password=password
        )

        assert result is not None
        assert "user" in result
        assert "access_token" in result

    @pytest.mark.asyncio
    async def test_authenticate_by_password_failure(
        self,
        mock_db_session,
        mock_repositories,
        mock_user
    ):
        """测试密码认证（失败）"""
        email = "test@example.com"
        password = "WrongPassword123!"

        # 配置mock：用户不存在
        mock_repositories["user_repo"].authenticate_by_password.return_value = None
        mock_repositories["login_history_repo"].create_login_record = AsyncMock()

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.user_repo = mock_repositories["user_repo"]
        service.session_repo = mock_repositories["session_repo"]
        service.login_history_repo = mock_repositories["login_history_repo"]

        # 执行认证并验证异常
        with pytest.raises(Exception) as exc_info:
            await service.authenticate_by_password(
                email=email,
                password=password
            )

    @pytest.mark.asyncio
    async def test_create_session(self, mock_db_session, mock_repositories):
        """测试创建会话"""
        user_id = "test-user-123"
        token_jti = "test-jti-123"
        refresh_token_jti = "test-refresh-jti-123"
        expires_at = datetime.utcnow() + timedelta(minutes=60)
        refresh_expires_at = datetime.utcnow() + timedelta(days=30)

        # 配置mock
        mock_repositories["session_repo"].create_session = AsyncMock()

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.session_repo = mock_repositories["session_repo"]

        # 执行创建会话
        result = await service.create_session(
            user_id=user_id,
            token_jti=token_jti,
            expires_at=expires_at,
            refresh_token_jti=refresh_token_jti,
            refresh_expires_at=refresh_expires_at
        )

        # 验证调用
        mock_repositories["session_repo"].create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_session(self, mock_db_session, mock_repositories):
        """测试撤销会话"""
        session_id = "test-session-123"
        user_id = "test-user-123"

        # 配置mock返回值
        mock_repositories["session_repo"].get_by_id.return_value = MagicMock()
        mock_repositories["session_repo"].revoke_session.return_value = True

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.session_repo = mock_repositories["session_repo"]

        # 执行撤销会话
        result = await service.revoke_session(session_id, user_id)

        # 验证调用
        mock_repositories["session_repo"].revoke_session.assert_called_once_with(
            session_id
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, mock_db_session, mock_repositories):
        """测试刷新访问令牌（成功）"""
        refresh_token = "test-refresh-token"
        user_id = "test-user-123"

        # 配置mock数据
        mock_session = MagicMock()
        mock_session.user_id = user_id
        mock_session.token_jti = "test-jti-123"
        mock_session.refresh_token_jti = "test-refresh-jti-123"
        mock_session.is_active = True
        mock_session.is_expired = False

        mock_repositories["session_repo"].get_by_refresh_token_jti.return_value = mock_session
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.is_active = True

        mock_repositories["user_repo"].get_by_id.return_value = mock_user
        mock_repositories["session_repo"].revoke_by_token_jti = AsyncMock(return_value=True)
        mock_repositories["session_repo"].create_session = AsyncMock()

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.user_repo = mock_repositories["user_repo"]
        service.session_repo = mock_repositories["session_repo"]

        # 执行刷新token
        result = await service.refresh_access_token(refresh_token)

        assert "access_token" in result
        assert result["expires_at"] > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_logout(self, mock_db_session, mock_repositories):
        """测试登出"""
        token_jti = "test-jti-123"
        user_id = "test-user-123"

        # 配置mock
        mock_repositories["session_repo"].revoke_by_token_jti = AsyncMock(return_value=True)

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.session_repo = mock_repositories["session_repo"]

        # 执行登出
        await service.logout(token_jti, user_id)

        # 验证调用
        mock_repositories["session_repo"].revoke_by_token_jti.assert_called_once_with(
            token_jti
        )

    @pytest.mark.asyncio
    async def test_logout_all(self, mock_db_session, mock_repositories):
        """测试登出所有设备"""
        user_id = "test-user-123"
        revoke_count = 3

        # 配置mock
        mock_repositories["session_repo"].revoke_all_sessions = AsyncMock(return_value=revoke_count)

        # 创建服务实例
        service = AuthService(mock_db_session)
        service.session_repo = mock_repositories["session_repo"]

        # 执行登出所有设备
        result = await service.logout_all(user_id)

        # 验证调用
        mock_repositories["session_repo"].revoke_all_sessions.assert_called_once_with(user_id)
        assert result == revoke_count
