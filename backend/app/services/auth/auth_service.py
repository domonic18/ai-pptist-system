"""
认证服务层
处理登录、注册、Token刷新、登出等认证业务逻辑
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status as http_status

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.repositories.login_history import LoginHistoryRepository
from app.core.auth.jwt_handler import jwt_handler
from app.core.auth.password_handler import password_handler
from app.core.log_utils import get_logger
from app.utils.id_utils import generate_uuid

logger = get_logger(__name__)


class AuthService:
    """认证服务 - 处理认证相关业务逻辑"""

    def __init__(self, db: AsyncSession):
        """初始化认证服务"""
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)
        self.login_history_repo = LoginHistoryRepository(db)

    async def authenticate_by_password(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        通过密码认证用户

        Args:
            email: 用户邮箱
            password: 用户密码
            ip_address: 客户端IP地址
            user_agent: 用户代理

        Returns:
            包含用户信息和token的字典

        Raises:
            HTTPException: 认证失败时抛出
        """
        # 验证用户
        user = await self.user_repo.authenticate_by_password(email, password)

        if not user:
            # 记录失败的登录尝试
            await self.login_history_repo.create_login_record(
                auth_type='password',
                login_status='failed',
                failure_reason='邮箱或密码错误',
                ip_address=ip_address,
                user_agent=user_agent
            )

            # 检查是否有暴力破解尝试
            failed_attempts = await self.login_history_repo.get_failed_login_attempts(
                ip_address=ip_address,
                minutes=30
            )

            if failed_attempts >= 5:
                logger.warning(f"检测到暴力破解尝试，IP: {ip_address}")

            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )

        # 创建 token 对
        token_data = jwt_handler.create_token_pair(
            user_id=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role
            }
        )

        # 创建会话记录
        await self.session_repo.create_session(
            user_id=user.id,
            token_jti=token_data["access_jti"],
            refresh_token_jti=token_data["refresh_jti"],
            expires_at=token_data["expires_at"],
            refresh_expires_at=token_data["refresh_expires_at"],
            user_agent=user_agent,
            ip_address=ip_address
        )

        # 记录成功的登录
        await self.login_history_repo.create_login_record(
            auth_type='password',
            login_status='success',
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        logger.info(f"用户登录成功: {user.email}")

        return {
            "user": user,
            **token_data
        }

    async def register_user(
        self,
        email: str,
        name: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        注册新用户

        Args:
            email: 用户邮箱
            name: 用户姓名
            password: 用户密码
            ip_address: 客户端IP地址
            user_agent: 用户代理

        Returns:
            包含用户信息和token的字典

        Raises:
            HTTPException: 注册失败时抛出
        """
        # 检查邮箱是否已存在
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册"
            )

        # 创建用户
        user = await self.user_repo.create_user(
            email=email,
            name=name,
            password=password,
            role='USER',
            auth_type='password'
        )

        # 创建 token 对
        token_data = jwt_handler.create_token_pair(
            user_id=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role
            }
        )

        # 创建会话记录
        await self.session_repo.create_session(
            user_id=user.id,
            token_jti=token_data["access_jti"],
            refresh_token_jti=token_data["refresh_jti"],
            expires_at=token_data["expires_at"],
            refresh_expires_at=token_data["refresh_expires_at"],
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(f"用户注册成功: {user.email}")

        return {
            "user": user,
            **token_data
        }

    async def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        刷新访问令牌（同时更新refresh令牌）

        为了避免数据库唯一索引锁冲突问题，每次刷新时：
        1. 生成新的 access_token 和 refresh_token
        2. 使用新的 refresh_jti 创建新会话
        3. 避免在同一事务中出现重复的 refresh_token_jti

        Args:
            refresh_token: 刷新令牌
            ip_address: 客户端IP地址
            user_agent: 用户代理

        Returns:
            包含新token的字典

        Raises:
            HTTPException: 刷新失败时抛出
        """
        import time
        start_time = time.time()
        logger.info("[SERVICE-REFRESH-START] AuthService.refresh_access_token 开始")

        # 验证刷新令牌
        verify_start = time.time()
        try:
            logger.info("[SERVICE-VERIFY-START] 开始验证刷新令牌")
            payload = jwt_handler.verify_refresh_token(refresh_token)
            user_id = payload.get("sub")
            old_refresh_jti = payload.get("jti")
            logger.info(f"[SERVICE-VERIFY-END] 令牌验证成功 - user_id: {user_id}, jti: {old_refresh_jti}, 耗时: {time.time() - verify_start:.3f}s")
        except Exception as e:
            logger.warning(f"[SERVICE-VERIFY-FAILED] 刷新令牌验证失败: {str(e)}, 耗时: {time.time() - verify_start:.3f}s")
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌无效或已过期"
            )

        # 查找会话记录
        session_start = time.time()
        logger.info(f"[SERVICE-SESSION-START] 开始查询会话记录 - refresh_jti: {old_refresh_jti}")
        session = await self.session_repo.get_by_refresh_token_jti(old_refresh_jti)
        logger.info(f"[SERVICE-SESSION-END] 会话查询完成 - 找到: {session is not None}, 活跃: {session.is_active if session else 'N/A'}, 耗时: {time.time() - session_start:.3f}s")

        if not session or not session.is_active:
            logger.warning(f"[SERVICE-SESSION-FAILED] 会话无效或已过期 - session: {session}, is_active: {session.is_active if session else 'N/A'}")
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="会话已过期或已撤销"
            )

        # 获取用户信息
        user_start = time.time()
        logger.info(f"[SERVICE-USER-START] 开始查询用户信息 - user_id: {user_id}")
        user = await self.user_repo.get_by_id(user_id)
        logger.info(f"[SERVICE-USER-END] 用户查询完成 - 找到: {user is not None}, 活跃: {user.is_active if user else 'N/A'}, 耗时: {time.time() - user_start:.3f}s")

        if not user or not user.is_active:
            logger.warning(f"[SERVICE-USER-FAILED] 用户不存在或已被禁用 - user: {user}, is_active: {user.is_active if user else 'N/A'}")
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )

        # 创建新的访问令牌
        create_token_start = time.time()
        logger.info("[SERVICE-CREATE-TOKEN-START] 开始创建新的访问令牌")
        access_token, access_jti, expires_at = jwt_handler.create_access_token(
            {"sub": user.id, "email": user.email, "role": user.role}
        )
        logger.info(f"[SERVICE-CREATE-TOKEN-END] 访问令牌创建完成 - access_jti: {access_jti}, 耗时: {time.time() - create_token_start:.3f}s")

        # 创建新的刷新令牌（关键修复：生成新的 refresh_jti 避免唯一约束冲突）
        logger.info("[SERVICE-CREATE-REFRESH-TOKEN-START] 开始创建新的刷新令牌")
        new_refresh_token, new_refresh_jti, new_refresh_expires_at = jwt_handler.create_refresh_token(
            {"sub": user.id, "email": user.email, "role": user.role}
        )
        logger.info(f"[SERVICE-CREATE-REFRESH-TOKEN-END] 刷新令牌创建完成 - new_refresh_jti: {new_refresh_jti}, 耗时: {time.time() - create_token_start:.3f}s")

        # 转换为 naive datetime 以兼容数据库
        expires_at_naive = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
        new_refresh_expires_at_naive = new_refresh_expires_at.replace(tzinfo=None) if new_refresh_expires_at.tzinfo else new_refresh_expires_at

        # 撤销旧会话并创建新会话（在一个事务中完成）
        revoke_create_start = time.time()
        logger.info(f"[SERVICE-REVOKE-CREATE-START] 开始撤销旧会话并创建新会话 - old_token_jti: {session.token_jti}, new_token_jti: {access_jti}")

        new_session = await self.session_repo.revoke_and_create_session(
            old_token_jti=session.token_jti,
            user_id=user.id,
            new_token_jti=access_jti,
            expires_at=expires_at_naive,
            refresh_token_jti=new_refresh_jti,  # 使用新的 refresh_jti
            refresh_expires_at=new_refresh_expires_at_naive,
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(f"[SERVICE-REVOKE-CREATE-END] 撤销并创建会话完成, 耗时: {time.time() - revoke_create_start:.3f}s")

        total_time = time.time() - start_time
        logger.info(f"[SERVICE-REFRESH-SUCCESS] Token刷新成功 - email: {user.email}, 总耗时: {total_time:.3f}s")

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,  # 返回新的 refresh token
            "expires_at": expires_at_naive,
            "refresh_expires_at": new_refresh_expires_at_naive
        }

    async def logout(
        self,
        token_jti: str,
        user_id: str
    ) -> None:
        """
        登出用户

        Args:
            token_jti: JWT Token ID
            user_id: 用户ID
        """
        # 撤销会话
        await self.session_repo.revoke_by_token_jti(token_jti)

        logger.info(f"用户登出: {user_id}")

    async def logout_all(self, user_id: str) -> int:
        """
        登出用户所有设备

        Args:
            user_id: 用户ID

        Returns:
            撤销的会话数
        """
        count = await self.session_repo.revoke_all_sessions(user_id)

        logger.info(f"用户所有设备登出: {user_id}, 撤销会话数: {count}")

        return count

    async def get_user_sessions(
        self,
        user_id: str,
        current_token_jti: str,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户的所有活跃会话

        Args:
            user_id: 用户ID
            current_token_jti: 当前token的JTI（用于标记当前会话）
            skip: 跳过记录数
            limit: 返回记录数限制

        Returns:
            包含会话列表和总数的字典
        """
        sessions = await self.session_repo.get_active_sessions(user_id, skip, limit)
        total = await self.session_repo.get_all_active_sessions_count(user_id)

        # 转换为响应格式
        session_list = []
        for session in sessions:
            session_list.append({
                "id": session.id,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "is_current": session.token_jti == current_token_jti
            })

        return {
            "sessions": session_list,
            "total": total
        }

    async def revoke_session(self, session_id: str, user_id: str) -> bool:
        """
        撤销指定会话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            是否撤销成功
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return await self.session_repo.revoke_session(session_id)
