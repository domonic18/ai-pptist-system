"""
登录历史数据访问层
"""

from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.sql.functions import count
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_history import LoginHistory
from app.repositories.base import BaseRepository
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class LoginHistoryRepository(BaseRepository):
    """登录历史Repository"""

    @property
    def model(self):
        return LoginHistory

    async def create_login_record(
        self,
        auth_type: str,
        login_status: str,
        user_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        saml_name_id: Optional[str] = None
    ) -> LoginHistory:
        """创建登录记录"""
        return await self.create(
            user_id=user_id,
            auth_type=auth_type,
            login_status=login_status,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            saml_name_id=saml_name_id
        )

    async def get_user_login_history(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[LoginHistory]:
        """获取用户登录历史"""
        stmt = (
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(LoginHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_login_attempts(
        self,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        minutes: int = 30
    ) -> int:
        """获取失败登录尝试次数（用于限制暴力破解）"""
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes)

        conditions = [
            LoginHistory.login_status == 'failed',
            LoginHistory.created_at >= cutoff_time
        ]

        if ip_address:
            conditions.append(LoginHistory.ip_address == ip_address)

        stmt = select(count(LoginHistory.id)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_recent_failed_logins_by_ip(
        self,
        ip_address: str,
        minutes: int = 30
    ) -> List[LoginHistory]:
        """获取最近失败的登录记录（按IP）"""
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes)

        stmt = (
            select(LoginHistory)
            .where(
                and_(
                    LoginHistory.ip_address == ip_address,
                    LoginHistory.login_status == 'failed',
                    LoginHistory.created_at >= cutoff_time
                )
            )
            .order_by(LoginHistory.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_login_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> dict:
        """获取用户登录统计"""
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        # 成功登录次数
        success_stmt = select(count(LoginHistory.id)).where(
            and_(
                LoginHistory.user_id == user_id,
                LoginHistory.login_status == 'success',
                LoginHistory.created_at >= cutoff_time
            )
        )
        success_result = await self.db.execute(success_stmt)
        success_count = success_result.scalar() or 0

        # 失败登录次数
        failed_stmt = select(count(LoginHistory.id)).where(
            and_(
                LoginHistory.user_id == user_id,
                LoginHistory.login_status == 'failed',
                LoginHistory.created_at >= cutoff_time
            )
        )
        failed_result = await self.db.execute(failed_stmt)
        failed_count = failed_result.scalar() or 0

        # 最后成功登录时间
        last_success_stmt = select(LoginHistory).where(
            and_(
                LoginHistory.user_id == user_id,
                LoginHistory.login_status == 'success'
            )
        ).order_by(LoginHistory.created_at.desc()).limit(1)
        last_success_result = await self.db.execute(last_success_stmt)
        last_success = last_success_result.scalar_one_or_none()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "last_success_at": last_success.created_at if last_success else None,
            "period_days": days
        }
