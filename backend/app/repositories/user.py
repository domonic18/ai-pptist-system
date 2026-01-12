"""
用户数据访问层
"""

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.core.log_utils import get_logger
from app.core.auth.password_handler import password_handler

logger = get_logger(__name__)


class UserRepository(BaseRepository):
    """用户Repository"""

    @property
    def model(self):
        return User

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_saml_name_id(self, saml_name_id: str) -> Optional[User]:
        """根据 SAML NameID 获取用户"""
        stmt = select(User).where(
            and_(
                User.auth_type == 'saml',
                User.saml_name_id == saml_name_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        name: str,
        password: str,
        role: str = 'USER',
        auth_type: str = 'password'
    ) -> User:
        """创建用户"""
        # 哈希密码
        hashed_password = password_handler.hash_password(password)

        return await self.create(
            email=email,
            name=name,
            password=hashed_password,
            role=role,
            auth_type=auth_type
        )

    async def create_sso_user(
        self,
        email: str,
        name: str,
        saml_name_id: str,
        saml_attributes: dict,
        role: str = 'USER'
    ) -> User:
        """创建 SSO 用户（无密码）"""
        import uuid
        random_password = uuid.uuid4().hex  # 生成随机密码（不会被使用）

        return await self.create(
            email=email,
            name=name,
            password=password_handler.hash_password(random_password),
            role=role,
            auth_type='saml',
            saml_name_id=saml_name_id,
            saml_attributes=saml_attributes
        )

    async def authenticate_by_password(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """通过密码认证用户"""
        user = await self.get_by_email(email)

        if not user:
            return None

        if user.auth_type != 'password':
            return None

        if not user.is_active:
            return None

        # 验证密码
        if not password_handler.verify_password(password, user.password):
            return None

        # 更新最后登录时间
        await self.update_last_login(user.id)

        return user

    async def update_last_login(self, user_id: str) -> None:
        """更新用户最后登录时间"""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_saml_info(
        self,
        user_id: str,
        saml_name_id: str,
        saml_session_index: str,
        saml_attributes: dict
    ) -> Optional[User]:
        """更新用户 SAML 信息"""
        return await self.update(
            user_id,
            saml_name_id=saml_name_id,
            saml_session_index=saml_session_index,
            saml_attributes=saml_attributes,
            last_sso_login_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )

    async def change_password(
        self,
        user_id: str,
        new_password: str
    ) -> bool:
        """修改密码"""
        hashed_password = password_handler.hash_password(new_password)
        result = await self.update(user_id, password=hashed_password)
        return result is not None

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[User], int]:
        """获取活跃用户列表"""
        # 获取总数
        count_stmt = select(User).where(User.is_active == True)
        count_result = await self.db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 获取分页数据
        stmt = (
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return list(users), total
