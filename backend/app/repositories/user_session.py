"""
用户会话数据访问层
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class UserSessionRepository(BaseRepository):
    """用户会话Repository"""

    @property
    def model(self):
        return UserSession

    async def create_session(
        self,
        user_id: str,
        token_jti: str,
        expires_at: datetime,
        refresh_token_jti: Optional[str] = None,
        refresh_expires_at: Optional[datetime] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """创建用户会话"""
        import time
        start_time = time.time()
        logger.info(f"[REPO-CREATE-SESSION-START] 创建会话 - user_id: {user_id}, token_jti: {token_jti}")

        session = await self.create(
            user_id=user_id,
            token_jti=token_jti,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(f"[REPO-CREATE-SESSION-END] 会话创建完成 - session_id: {session.id}, 耗时: {time.time() - start_time:.3f}s")
        return session

    async def get_by_token_jti(self, token_jti: str) -> Optional[UserSession]:
        """根据 Token JTI 获取会话"""
        stmt = select(UserSession).where(UserSession.token_jti == token_jti)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_refresh_token_jti(self, refresh_token_jti: str) -> Optional[UserSession]:
        """根据刷新 Token JTI 获取会话"""
        import time
        start_time = time.time()
        logger.info(f"[REPO-SESSION-START] 查询会话 - refresh_token_jti: {refresh_token_jti}")

        stmt = select(UserSession).where(
            and_(
                UserSession.refresh_token_jti == refresh_token_jti,
                UserSession.revoked_at.is_(None)
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        logger.info(f"[REPO-SESSION-END] 查询完成 - 找到: {session is not None}, 耗时: {time.time() - start_time:.3f}s")
        return session

    async def get_active_sessions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[UserSession]:
        """获取用户活跃会话列表"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > now
                )
            )
            .order_by(UserSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active_sessions_count(self, user_id: str) -> int:
        """获取用户活跃会话总数"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(count(UserSession.id)).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def revoke_session(self, session_id: str) -> bool:
        """撤销会话"""
        session = await self.get_by_id(session_id)
        if not session:
            return False

        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True

    async def revoke_by_token_jti(self, token_jti: str) -> bool:
        """根据 Token JTI 撤销会话"""
        import time
        start_time = time.time()
        logger.info(f"[REPO-REVOKE-START] 撤销会话 - token_jti: {token_jti}")

        stmt = (
            update(UserSession)
            .where(UserSession.token_jti == token_jti)
            .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        logger.info(f"[REPO-REVOKE-END] 撤销完成 - 影响行数: {result.rowcount}, 耗时: {time.time() - start_time:.3f}s")
        return result.rowcount > 0

    async def revoke_all_sessions(self, user_id: str) -> int:
        """撤销用户所有会话"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            update(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None)
                )
            )
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def clean_expired_sessions(self, days: int = 1) -> int:
        """清理过期会话（已过期且已撤销超过指定天数）"""
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        expired_time = datetime.now(timezone.utc).replace(tzinfo=None)

        # 先获取符合条件的会话数量
        count_stmt = select(count(UserSession.id)).where(
            and_(
                UserSession.revoked_at.is_not(None),
                UserSession.expires_at < expired_time,
                UserSession.revoked_at < cutoff_time
            )
        )
        count_result = await self.db.execute(count_stmt)
        count = count_result.scalar() or 0

        # 删除这些会话
        from sqlalchemy import delete
        delete_stmt = delete(UserSession).where(
            and_(
                UserSession.revoked_at.is_not(None),
                UserSession.expires_at < expired_time,
                UserSession.revoked_at < cutoff_time
            )
        )
        await self.db.execute(delete_stmt)
        await self.db.commit()

        logger.info(f"清理过期会话: {count} 个")
        return count

    async def is_session_active(self, token_jti: str) -> bool:
        """检查会话是否活跃"""
        session = await self.get_by_token_jti(token_jti)
        if not session:
            return False
        return session.is_active

    async def revoke_and_create_session(
        self,
        old_token_jti: str,
        user_id: str,
        new_token_jti: str,
        expires_at: datetime,
        refresh_token_jti: Optional[str] = None,
        refresh_expires_at: Optional[datetime] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """
        撤销旧会话并创建新会话（在一个事务中完成）
        避免多次commit导致的连接问题

        Args:
            old_token_jti: 要撤销的旧token的JTI
            user_id: 用户ID
            new_token_jti: 新token的JTI
            expires_at: 新token的过期时间
            refresh_token_jti: 刷新token的JTI
            refresh_expires_at: 刷新token的过期时间
            user_agent: 用户代理
            ip_address: IP地址

        Returns:
            新创建的会话
        """
        import time
        start_time = time.time()
        logger.info(f"[REPO-REVOKE-CREATE-START] 撤销旧会话并创建新会话 - old_token_jti: {old_token_jti}, new_token_jti: {new_token_jti}")

        # 步骤1: 撤销旧会话
        revoke_start = time.time()
        logger.info(f"[REPO-REVOKE-CREATE-STEP1] 开始撤销旧会话")
        stmt = (
            update(UserSession)
            .where(UserSession.token_jti == old_token_jti)
            .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        revoke_result = await self.db.execute(stmt)
        logger.info(f"[REPO-REVOKE-CREATE-STEP1-END] 旧会话撤销完成 - 影响行数: {revoke_result.rowcount}, 耗时: {time.time() - revoke_start:.3f}s")

        # 步骤2: 创建新会话
        create_start = time.time()
        logger.info(f"[REPO-REVOKE-CREATE-STEP2] 开始创建新会话")

        # 生成UUID
        from app.utils.id_utils import generate_uuid
        session_id = generate_uuid()

        new_session = UserSession(
            id=session_id,
            user_id=user_id,
            token_jti=new_token_jti,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        self.db.add(new_session)

        logger.info(f"[REPO-REVOKE-CREATE-STEP2-END] 新会话添加到数据库 - session_id: {session_id}, 耗时: {time.time() - create_start:.3f}s")

        # 步骤3: 统一提交
        commit_start = time.time()
        logger.info(f"[REPO-REVOKE-CREATE-STEP3] 开始提交事务")
        await self.db.commit()
        logger.info(f"[REPO-REVOKE-CREATE-STEP3-END] 事务提交完成, 耗时: {time.time() - commit_start:.3f}s")

        # 刷新实例
        await self.db.refresh(new_session)

        logger.info(f"[REPO-REVOKE-CREATE-DONE] 撤销并创建完成 - 总耗时: {time.time() - start_time:.3f}s")
        return new_session
