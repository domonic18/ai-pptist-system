"""
密码处理器
负责密码哈希、验证和强度校验
"""

import re
from typing import Optional
from passlib.context import CryptContext

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class PasswordHandler:
    """密码处理器"""

    def __init__(self):
        """初始化密码处理器"""
        self.bcrypt_rounds = settings.PASSWORD_BCRYPT_ROUNDS
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.min_length = settings.PASSWORD_MIN_LENGTH
        self.require_uppercase = settings.PASSWORD_REQUIRE_UPPERCASE
        self.require_lowercase = settings.PASSWORD_REQUIRE_LOWERCASE
        self.require_digit = settings.PASSWORD_REQUIRE_DIGIT
        self.require_special = settings.PASSWORD_REQUIRE_SPECIAL
        self.special_chars = settings.PASSWORD_SPECIAL_CHARS

    def hash_password(self, password: str) -> str:
        """
        对密码进行哈希

        Args:
            password: 明文密码

        Returns:
            哈希后的密码

        Raises:
            ValueError: 密码不符合强度要求
        """
        # 验证密码强度
        self.validate_password_strength(password)

        # 使用 bcrypt 进行哈希
        hashed = self.pwd_context.hash(password)

        logger.info(
            "密码哈希完成",
            extra={
                "rounds": self.bcrypt_rounds,
                "length": len(password)
            }
        )

        return hashed

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码

        Args:
            plain_password: 明文密码
            hashed_password: 哈希后的密码

        Returns:
            密码是否匹配
        """
        is_valid = self.pwd_context.verify(plain_password, hashed_password)

        if not is_valid:
            logger.warning("密码验证失败")

        return is_valid

    def validate_password_strength(
        self,
        password: str,
        raise_error: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        验证密码强度

        Args:
            password: 要验证的密码
            raise_error: 是否在验证失败时抛出异常

        Returns:
            (is_valid, error_message) - 是否有效和错误消息

        Raises:
            ValueError: 密码不符合强度要求且 raise_error=True
        """
        errors = []

        # 检查长度
        if len(password) < self.min_length:
            errors.append(f"密码长度至少需要 {self.min_length} 位")

        # 检查大写字母
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含至少一个大写字母")

        # 检查小写字母
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("密码必须包含至少一个小写字母")

        # 检查数字
        if self.require_digit and not re.search(r'\d', password):
            errors.append("密码必须包含至少一个数字")

        # 检查特殊字符
        if self.require_special:
            has_special = any(c in self.special_chars for c in password)
            if not has_special:
                errors.append(f"密码必须包含至少一个特殊字符 ({self.special_chars})")

        is_valid = len(errors) == 0
        error_message = "; ".join(errors) if errors else None

        if not is_valid and raise_error:
            raise ValueError(error_message)

        return is_valid, error_message

    def get_password_strength_score(self, password: str) -> dict:
        """
        获取密码强度评分

        Args:
            password: 要评估的密码

        Returns:
            包含强度分数和详细信息的字典
        """
        score = 0
        details = []

        # 长度评分 (最多40分)
        length = len(password)
        if length >= 12:
            score += 40
            details.append("长度: 优秀")
        elif length >= 8:
            score += 30
            details.append("长度: 良好")
        elif length >= 6:
            score += 20
            details.append("长度: 一般")
        else:
            details.append("长度: 过短")

        # 大写字母 (15分)
        if re.search(r'[A-Z]', password):
            score += 15
            details.append("包含大写字母")

        # 小写字母 (15分)
        if re.search(r'[a-z]', password):
            score += 15
            details.append("包含小写字母")

        # 数字 (15分)
        if re.search(r'\d', password):
            score += 15
            details.append("包含数字")

        # 特殊字符 (15分)
        if any(c in self.special_chars for c in password):
            score += 15
            details.append("包含特殊字符")

        # 确定强度等级
        if score >= 80:
            strength = "强"
        elif score >= 60:
            strength = "中"
        elif score >= 40:
            strength = "弱"
        else:
            strength = "很弱"

        return {
            "score": score,
            "strength": strength,
            "details": details
        }

    def generate_random_password(self, length: int = 16) -> str:
        """
        生成随机密码

        Args:
            length: 密码长度

        Returns:
            随机密码
        """
        import secrets
        import string

        # 确保密码包含各种类型的字符
        alphabet = (
            string.ascii_uppercase +
            string.ascii_lowercase +
            string.digits +
            self.special_chars
        )

        password = ''.join(secrets.choice(alphabet) for _ in range(length))

        # 确保生成的密码符合强度要求
        is_valid, _ = self.validate_password_strength(password, raise_error=False)
        if not is_valid:
            # 如果随机生成的密码不符合要求，递归重试
            return self.generate_random_password(length)

        logger.info("生成随机密码")
        return password


# 全局密码处理器实例
password_handler = PasswordHandler()
