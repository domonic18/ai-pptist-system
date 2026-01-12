"""
认证中间件
提供用户认证和权限验证的依赖注入
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.auth.jwt_handler import jwt_handler
from app.core.log_utils import get_logger

logger = get_logger(__name__)

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """
    获取当前用户（可选认证）

    Args:
        credentials: HTTP Bearer 认证凭证
        db: 数据库会话

    Returns:
        用户信息字典，如果未认证则返回 None
    """
    if not credentials:
        return None

    try:
        # 验证 token
        payload = jwt_handler.verify_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if not user_id:
            return None

        # 查询用户
        from app.repositories.user import UserRepository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser
        }

    except Exception as e:
        logger.warning(f"获取用户失败: {str(e)}")
        return None


async def get_current_user(
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> dict:
    """
    获取当前用户（必须认证）

    Args:
        current_user: 可选认证的用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 未认证时抛出 401 错误
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    获取当前活跃用户

    Args:
        current_user: 认证的用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 用户未激活时抛出 403 错误
    """
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )
    return current_user


async def get_current_superuser(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    获取当前超级用户

    Args:
        current_user: 认证的用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 非超级用户时抛出 403 错误
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级用户权限"
        )
    return current_user


class RequireAuth:
    """
    认证要求装饰器类

    用于在端点上添加认证要求
    """

    @staticmethod
    def auth_required() -> Depends:
        """要求认证"""
        return Depends(get_current_user)

    @staticmethod
    def active_required() -> Depends:
        """要求活跃用户"""
        return Depends(get_current_active_user)

    @staticmethod
    def superuser_required() -> Depends:
        """要求超级用户"""
        return Depends(get_current_superuser)


# 便捷依赖函数
require_auth = RequireAuth()
