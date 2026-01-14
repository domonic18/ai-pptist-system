"""
SAML认证服务层
处理SAML SSO登录、用户自动创建、会话管理
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status as http_status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from onelogin.saml2.auth import OneLogin_Saml2_Auth

from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.repositories.login_history import LoginHistoryRepository
from app.core.auth.jwt_handler import jwt_handler
from app.core.config.saml_config import saml_settings
from app.core.log_utils import get_logger
from app.utils.id_utils import generate_uuid
from app.core.exceptions.saml import (
    SAMLValidationError,
    SAMLMetadataError
)

logger = get_logger(__name__)


class SAMLAuthService:
    """SAML认证服务 - 处理SAML SSO业务逻辑"""

    def __init__(self, db: AsyncSession):
        """初始化SAML认证服务"""
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
        self.login_history_repo = LoginHistoryRepository(db)

    async def _prepare_request_dict(self, request: Request) -> Dict[str, Any]:
        """
        准备SAML请求字典（异步版本）

        Args:
            request: FastAPI Request对象

        Returns:
            SAML请求字典
        """
        # 获取URL信息
        url = request.url

        # 提取POST数据（SAML Response）
        post_data = {}
        if request.method == "POST":
            # SAML Response通常在POST表单数据中
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                # 在异步上下文中正确获取表单数据
                try:
                    body = await request.body()
                    from urllib.parse import parse_qs
                    form_data = parse_qs(body.decode('utf-8'))
                    post_data = {k: v[0] if v else '' for k, v in form_data.items()}
                except Exception as e:
                    logger.warning(f"获取POST表单数据失败: {e}")
                    post_data = {}

        return {
            'https': 'on' if url.scheme == 'https' else 'off',
            'http_host': url.hostname,
            'server_port': url.port if url.port else (443 if url.scheme == 'https' else 80),
            'script_name': str(request.scope.get('path', url.path)),
            'get_data': dict(request.query_params),
            'post_data': post_data,
            'request_uri': str(url),
        }

    async def init_saml_auth(self, request: Request) -> OneLogin_Saml2_Auth:
        """
        初始化SAML认证对象（异步版本）

        Args:
            request: FastAPI Request对象

        Returns:
            OneLogin_Saml2_Auth实例
        """
        req_dict = await self._prepare_request_dict(request)

        # 使用SAML配置加载器加载完整配置
        saml_settings_dict = saml_settings.load_saml_config()

        return OneLogin_Saml2_Auth(req_dict, old_settings=saml_settings_dict)

    async def initiate_sso_login(
        self,
        request: Request,
        return_to: Optional[str] = None
    ) -> str:
        """
        发起SSO登录

        Args:
            request: FastAPI Request对象
            return_to: 登录成功后重定向URL（可选）

        Returns:
            IdP登录URL
        """
        auth = await self.init_saml_auth(request)

        # 生成登录URL
        login_url = auth.login(return_to=return_to)

        # 存储AuthNRequest ID用于后续验证（防重放攻击）
        request_id = auth.get_last_request_id()
        if request_id:
            logger.info(f"生成SAML AuthNRequest ID: {request_id}")
            # TODO: 存储到Redis或数据库，设置过期时间

        logger.info(f"发起SSO登录，重定向到IdP: {login_url}")
        return login_url

    async def process_acs_response(
        self,
        request: Request,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理SAML ACS响应

        Args:
            request: FastAPI Request对象
            ip_address: 客户端IP地址
            user_agent: 用户代理

        Returns:
            包含用户信息和token的字典

        Raises:
            SAMLValidationError: SAML验证失败
        """
        logger.info("[SSO-ACS-START] 开始处理SAML ACS响应")

        auth = await self.init_saml_auth(request)

        # 验证SAML Response
        request_id = None  # TODO: 从Redis或数据库获取之前存储的request_id
        auth.process_response(request_id=request_id)

        # 检查错误
        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            logger.error(f"[SSO-ACS-ERROR] SAML验证失败 - errors: {errors}, reason: {error_reason}")

            # 记录失败的登录尝试
            await self.login_history_repo.create_login_record(
                auth_type='saml',
                login_status='failed',
                failure_reason=f'SAML验证失败: {error_reason}',
                ip_address=ip_address,
                user_agent=user_agent
            )

            raise SAMLValidationError(
                message=f"SAML认证失败: {error_reason}",
                details={"errors": errors}
            )

        # 检查是否认证成功
        if not auth.is_authenticated():
            logger.error("[SSO-ACS-ERROR] SAML认证失败: 未通过身份验证")
            raise SAMLValidationError(
                message="SAML身份验证失败",
                details={"reason": "未通过身份验证"}
            )

        # 提取用户信息
        saml_name_id = auth.get_nameid()
        saml_session_index = auth.get_session_index()
        saml_attributes = auth.get_attributes()

        logger.info(f"[SSO-ACS-SUCCESS] SAML用户认证成功 - NameID: {saml_name_id}")
        logger.debug(f"[SSO-ACS-ATTRIBUTES] SAML属性: {saml_attributes}")

        # 从SAML属性中提取用户信息
        user_email = self._extract_email(saml_attributes, saml_name_id)
        user_name = self._extract_name(saml_attributes, saml_name_id)

        logger.info(f"[SSO-ACS-USER-INFO] 提取用户信息 - email: {user_email}, name: {user_name}")

        # 查找或创建用户
        logger.info(f"[SSO-ACS-GET-USER] 开始获取或创建SSO用户 - email: {user_email}")
        user = await self._get_or_create_sso_user(
            email=user_email,
            name=user_name,
            saml_name_id=saml_name_id,
            saml_session_index=saml_session_index,
            saml_attributes=saml_attributes
        )
        logger.info(f"[SSO-ACS-USER-DONE] 用户处理完成 - user_id: {user.id}, email: {user.email}, auth_type: {user.auth_type}")

        # 创建JWT Token
        logger.info(f"[SSO-ACS-TOKEN-START] 开始创建JWT Token - user_id: {user.id}")
        token_data = jwt_handler.create_token_pair(
            user_id=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role
            }
        )
        logger.info(f"[SSO-ACS-TOKEN-DONE] JWT Token创建成功 - access_jti: {token_data.get('access_jti')}, refresh_jti: {token_data.get('refresh_jti')}")

        # 创建会话记录
        logger.info(f"[SSO-ACS-SESSION-START] 开始创建会话记录")
        await self.session_repo.create_session(
            user_id=user.id,
            token_jti=token_data["access_jti"],
            refresh_token_jti=token_data["refresh_jti"],
            expires_at=token_data["expires_at"],
            refresh_expires_at=token_data["refresh_expires_at"],
            user_agent=user_agent,
            ip_address=ip_address
        )
        logger.info(f"[SSO-ACS-SESSION-DONE] 会话记录创建成功")

        # 记录成功的登录
        await self.login_history_repo.create_login_record(
            auth_type='saml',
            login_status='success',
            user_id=user.id,
            saml_name_id=saml_name_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        logger.info(f"[SSO-ACS-COMPLETE] SSO用户登录成功 - email: {user.email}, user_id: {user.id}")

        return {
            "user": user,
            **token_data
        }

    def _extract_email(
        self,
        saml_attributes: Dict[str, Any],
        saml_name_id: str
    ) -> str:
        """
        从SAML属性中提取邮箱

        Args:
            saml_attributes: SAML属性字典
            saml_name_id: SAML NameID

        Returns:
            用户邮箱
        """
        # 尝试从常见属性中获取邮箱
        email_attributes = [
            'email', 'Email', 'mail',
            'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
        ]

        for attr in email_attributes:
            if attr in saml_attributes and saml_attributes[attr]:
                email = saml_attributes[attr][0]
                if isinstance(email, str) and '@' in email:
                    return email

        # 如果没有找到邮箱属性，使用NameID（如果它是邮箱格式）
        if '@' in saml_name_id:
            return saml_name_id

        # 最后使用默认格式
        return f"{saml_name_id}@sso.user"

    def _extract_name(
        self,
        saml_attributes: Dict[str, Any],
        saml_name_id: str
    ) -> str:
        """
        从SAML属性中提取姓名

        Args:
            saml_attributes: SAML属性字典
            saml_name_id: SAML NameID

        Returns:
            用户姓名
        """
        # 尝试从常见属性中获取姓名
        name_attributes = [
            'displayName', 'DisplayName', 'displayname',
            'name', 'Name', 'cn', 'commonName',
            'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'
        ]

        for attr in name_attributes:
            if attr in saml_attributes and saml_attributes[attr]:
                name = saml_attributes[attr][0]
                if isinstance(name, str) and name.strip():
                    return name.strip()

        # 如果没有找到姓名属性，使用NameID
        return saml_name_id

    async def _get_or_create_sso_user(
        self,
        email: str,
        name: str,
        saml_name_id: str,
        saml_session_index: str,
        saml_attributes: Dict[str, Any]
    ) -> Any:
        """
        获取或创建SSO用户

        Args:
            email: 用户邮箱
            name: 用户姓名
            saml_name_id: SAML NameID
            saml_session_index: SAML SessionIndex
            saml_attributes: SAML属性字典

        Returns:
            User对象
        """
        # 先尝试通过SAML NameID查找
        user = await self.user_repo.get_by_saml_name_id(saml_name_id)

        if user:
            # 更新现有用户的SAML信息
            user = await self.user_repo.update_saml_info(
                user_id=user.id,
                saml_name_id=saml_name_id,
                saml_session_index=saml_session_index,
                saml_attributes=saml_attributes
            )
            logger.info(f"更新现有SSO用户: {user.email}")
            return user

        # 再尝试通过邮箱查找（可能是首次SSO登录的已有用户）
        user = await self.user_repo.get_by_email(email)

        if user:
            # 如果用户存在但不是SSO用户，更新为SSO用户
            if user.auth_type != 'saml':
                logger.warning(f"用户 {email} 从 {user.auth_type} 认证切换到 SAML 认证")

            user = await self.user_repo.update_saml_info(
                user_id=user.id,
                saml_name_id=saml_name_id,
                saml_session_index=saml_session_index,
                saml_attributes=saml_attributes
            )
            logger.info(f"将现有用户转换为SSO用户: {user.email}")
            return user

        # 创建新的SSO用户
        user = await self.user_repo.create_sso_user(
            email=email,
            name=name,
            saml_name_id=saml_name_id,
            saml_attributes=saml_attributes,
            role='USER'
        )
        logger.info(f"创建新SSO用户: {user.email}")
        return user

    async def initiate_slo(
        self,
        request: Request,
        saml_name_id: Optional[str] = None,
        saml_session_index: Optional[str] = None
    ) -> str:
        """
        发起单点登出

        Args:
            request: FastAPI Request对象
            saml_name_id: SAML NameID
            saml_session_index: SAML SessionIndex

        Returns:
            IdP登出URL
        """
        auth = await self.init_saml_auth(request)

        # 生成登出URL
        logout_url = auth.logout(
            name_id=saml_name_id,
            session_index=saml_session_index
        )

        logger.info(f"发起SLO，重定向到IdP: {logout_url}")
        return logout_url

    async def process_slo_response(
        self,
        request: Request,
        delete_session_cb: Optional[callable] = None
    ) -> bool:
        """
        处理SLO响应

        Args:
            request: FastAPI Request对象
            delete_session_cb: 删除会话的回调函数

        Returns:
            是否处理成功
        """
        auth = await self.init_saml_auth(request)

        # 处理SLO响应
        url = auth.process_slo(delete_session_cb=delete_session_cb)

        # 检查错误
        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            logger.error(f"SLO处理失败: {errors}, 原因: {error_reason}")
            return False

        logger.info("SLO处理成功")
        return True

    def get_sp_metadata(self) -> str:
        """
        获取SP元数据

        Returns:
            SP元数据XML字符串

        Raises:
            SAMLMetadataError: 元数据生成失败
        """
        try:
            # 加载SAML配置
            saml_settings_dict = saml_settings.load_saml_config()

            # 创建临时的SAML auth对象来获取元数据
            auth = OneLogin_Saml2_Auth({}, old_settings=saml_settings_dict)
            settings = auth.get_settings()
            metadata = settings.get_sp_metadata()

            # 验证元数据
            errors = settings.validate_metadata(metadata)
            if errors:
                logger.error(f"SP元数据验证失败: {errors}")
                raise SAMLMetadataError(
                    message="SP元数据生成失败",
                    details={"errors": errors}
                )

            return metadata

        except Exception as e:
            logger.error(f"生成SP元数据时发生错误: {str(e)}")
            raise SAMLMetadataError(
                message=f"生成SP元数据失败: {str(e)}",
                details={"exception": str(e)}
            )
