"""
JWT Token 处理器
负责 JWT Token 的生成、验证和刷新
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class JWTHandler:
    """JWT Token 处理器"""

    def __init__(self):
        """初始化 JWT 处理器"""
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str, datetime]:
        """
        创建访问令牌

        Args:
            data: 要编码到 token 中的数据
            expires_delta: 自定义过期时间

        Returns:
            (token, jti, expires_at) - 令牌、JWT ID、过期时间
        """
        # 生成唯一的 JWT ID
        jti = str(uuid.uuid4())

        # 计算过期时间
        if expires_delta:
            expires_at = datetime.now(timezone.utc) + expires_delta
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        # 准备 token 载荷
        to_encode = data.copy()
        to_encode.update({
            "jti": jti,
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        })

        # 编码 token
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "创建访问令牌",
            extra={
                "jti": jti,
                "user_id": data.get("sub"),
                "expires_at": expires_at.isoformat()
            }
        )

        return encoded_jwt, jti, expires_at

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str, datetime]:
        """
        创建刷新令牌

        Args:
            data: 要编码到 token 中的数据
            expires_delta: 自定义过期时间

        Returns:
            (token, jti, expires_at) - 令牌、JWT ID、过期时间
        """
        # 生成唯一的 JWT ID
        jti = str(uuid.uuid4())

        # 计算过期时间（刷新令牌有效期更长）
        if expires_delta:
            expires_at = datetime.now(timezone.utc) + expires_delta
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        # 准备 token 载荷
        to_encode = data.copy()
        to_encode.update({
            "jti": jti,
            "type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        })

        # 编码 token
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        logger.info(
            "创建刷新令牌",
            extra={
                "jti": jti,
                "user_id": data.get("sub"),
                "expires_at": expires_at.isoformat()
            }
        )

        return encoded_jwt, jti, expires_at

    def create_token_pair(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建令牌对（访问令牌 + 刷新令牌）

        Args:
            user_id: 用户ID
            additional_claims: 额外的声明

        Returns:
            包含 access_token, refresh_token, expires_at, refresh_expires_at 的字典
        """
        # 准备基础数据
        data = {"sub": user_id}
        if additional_claims:
            data.update(additional_claims)

        # 创建访问令牌
        access_token, access_jti, expires_at = self.create_access_token(data)

        # 创建刷新令牌
        refresh_token, refresh_jti, refresh_expires_at = self.create_refresh_token(data)

        # 转换为 naive datetime（移除时区信息）以兼容数据库
        # PostgreSQL TIMESTAMP 不存储时区信息
        expires_at_naive = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
        refresh_expires_at_naive = refresh_expires_at.replace(tzinfo=None) if refresh_expires_at.tzinfo else refresh_expires_at

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_jti": access_jti,
            "refresh_jti": refresh_jti,
            "expires_at": expires_at_naive,
            "refresh_expires_at": refresh_expires_at_naive
        }

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        解码并验证 token

        Args:
            token: JWT token 字符串

        Returns:
            解码后的 token 载荷

        Raises:
            JWTError: token 无效或过期
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"Token解码失败: {str(e)}")
            raise

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        验证访问令牌

        Args:
            token: 访问令牌

        Returns:
            token 载荷

        Raises:
            JWTError: token 无效、过期或类型错误
        """
        payload = self.decode_token(token)

        # 验证 token 类型
        token_type = payload.get("type")
        if token_type != "access":
            raise JWTError(f"无效的token类型: {token_type}")

        return payload

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        验证刷新令牌

        Args:
            token: 刷新令牌

        Returns:
            token 载荷

        Raises:
            JWTError: token 无效、过期或类型错误
        """
        payload = self.decode_token(token)

        # 验证 token 类型
        token_type = payload.get("type")
        if token_type != "refresh":
            raise JWTError(f"无效的token类型: {token_type}")

        return payload

    def get_token_jti(self, token: str) -> str:
        """
        从 token 中获取 JWT ID

        Args:
            token: JWT token 字符串

        Returns:
            JWT ID (jti)

        Raises:
            JWTError: token 无效
        """
        payload = self.decode_token(token)
        jti = payload.get("jti")
        if not jti:
            raise JWTError("Token中缺少jti声明")
        return jti

    def get_user_id_from_token(self, token: str) -> str:
        """
        从 token 中获取用户ID

        Args:
            token: JWT token 字符串

        Returns:
            用户ID

        Raises:
            JWTError: token 无效或缺少用户ID
        """
        payload = self.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("Token中缺少用户ID")
        return user_id

    def is_token_expired(self, token: str) -> bool:
        """
        检查 token 是否过期

        Args:
            token: JWT token 字符串

        Returns:
            True if expired, False otherwise
        """
        try:
            payload = self.decode_token(token)
            exp = payload.get("exp")
            if not exp:
                return True
            return datetime.now(timezone.utc) > datetime.fromtimestamp(exp, tz=timezone.utc)
        except JWTError:
            return True


# 全局 JWT 处理器实例
jwt_handler = JWTHandler()
