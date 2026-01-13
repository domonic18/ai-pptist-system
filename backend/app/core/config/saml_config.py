"""
SAML配置模块
负责加载和管理 SAML SSO 认证相关配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from app.utils.config_utils import get_backend_path, get_config_path


class SAMLConfigLoader:
    """SAML配置加载器 - 从配置文件加载并处理SAML配置"""

    def __init__(
        self,
        settings_file: str = "saml/settings.json",
        advanced_settings_file: str = "saml/advanced_settings.json",
        base_path: Optional[Path] = None
    ):
        """
        初始化 SAML 配置加载器

        Args:
            settings_file: SAML基础配置文件路径（相对于backend目录）
            advanced_settings_file: SAML高级配置文件路径（相对于backend目录）
            base_path: 配置文件的基础路径，默认为backend目录
        """
        self.base_path = base_path or get_backend_path()
        self.settings_file = self.base_path / settings_file
        self.advanced_settings_file = self.base_path / advanced_settings_file

        # 缓存加载的配置
        self._settings_cache: Optional[Dict[str, Any]] = None
        self._advanced_settings_cache: Optional[Dict[str, Any]] = None

    def _replace_env_variables(self, config: Any) -> Any:
        """
        递归替换配置中的环境变量占位符

        支持的占位符格式：
        - ${VARIABLE_NAME}
        - ${VARIABLE_NAME:default_value}

        Args:
            config: 配置对象（可以是字典、列表或字符串）

        Returns:
            替换环境变量后的配置对象
        """
        if isinstance(config, dict):
            return {key: self._replace_env_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_variables(item) for item in config]
        elif isinstance(config, str):
            return self._replace_env_in_string(config)
        else:
            return config

    def _replace_env_in_string(self, value: str) -> str:
        """
        替换字符串中的环境变量占位符

        Args:
            value: 包含占位符的字符串

        Returns:
            替换后的字符串
        """
        import re

        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default} 格式
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, value)

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        加载JSON配置文件

        Args:
            file_path: JSON文件路径

        Returns:
            解析后的字典

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON格式错误
        """
        if not file_path.exists():
            logger.warning(f"SAML配置文件不存在: {file_path}，使用默认配置")
            # 返回空配置，将由环境变量填充
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_settings(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载 SAML 基础配置

        Args:
            use_cache: 是否使用缓存的配置

        Returns:
            SAML基础配置字典，已替换环境变量

        Raises:
            FileNotFoundError: 配置文件不存在（已改为警告）
        """
        if use_cache and self._settings_cache is not None:
            return self._settings_cache

        try:
            raw_config = self._load_json_file(self.settings_file)
        except Exception as e:
            logger.warning(f"加载SAML配置文件失败: {e}，使用默认配置")
            raw_config = {}

        # 如果配置文件为空，使用环境变量构建默认配置
        if not raw_config:
            raw_config = self._build_default_config()

        self._settings_cache = self._replace_env_variables(raw_config)
        return self._settings_cache

    def _build_default_config(self) -> Dict[str, Any]:
        """
        从环境变量构建默认SAML配置

        Returns:
            SAML配置字典
        """
        return {
            "strict": os.environ.get("SAML_STRICT", "false").lower() == "true",
            "debug": os.environ.get("SAML_DEBUG", "true").lower() == "true",
            "sp": {
                "entityId": "${SAML_SP_ENTITY_ID}",
                "assertionConsumerService": {
                    "url": "${SAML_ACS_URL}",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": "${SAML_SLS_URL}",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:transient",
                "x509cert": "${SAML_SP_CERT}",
                "privateKey": "${SAML_SP_KEY}"
            },
            "idp": {
                "entityId": "${SAML_IDP_ENTITY_ID}",
                "singleSignOnService": {
                    "url": "${SAML_IDP_SSO_URL}",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": "${SAML_IDP_SLS_URL}",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": "${SAML_IDP_CERT}"
            }
        }

    def load_advanced_settings(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载 SAML 高级配置

        Args:
            use_cache: 是否使用缓存的配置

        Returns:
            SAML高级配置字典，已替换环境变量

        Raises:
            FileNotFoundError: 配置文件不存在
        """
        if use_cache and self._advanced_settings_cache is not None:
            return self._advanced_settings_cache

        raw_config = self._load_json_file(self.advanced_settings_file)
        self._advanced_settings_cache = self._replace_env_variables(raw_config)
        return self._advanced_settings_cache

    def load_all_settings(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载完整的 SAML 配置（基础配置 + 高级配置）

        Args:
            use_cache: 是否使用缓存的配置

        Returns:
            合并后的完整配置字典
        """
        settings = self.load_settings(use_cache)
        advanced_settings = self.load_advanced_settings(use_cache)

        # 合并配置（advanced_settings 会覆盖 settings 中的同名键）
        return {**settings, **advanced_settings}

    def reload(self):
        """清除缓存，强制下次重新加载配置文件"""
        self._settings_cache = None
        self._advanced_settings_cache = None

    def get_sp_entity_id(self) -> str:
        """获取 SP EntityID"""
        settings = self.load_settings()
        return settings.get("sp", {}).get("entityId", "")

    def get_idp_entity_id(self) -> str:
        """获取 IDP EntityID"""
        settings = self.load_settings()
        return settings.get("idp", {}).get("entityId", "")

    def get_sso_url(self) -> str:
        """获取 IDP SSO URL"""
        settings = self.load_settings()
        return settings.get("idp", {}).get("singleSignOnService", {}).get("url", "")

    def get_sls_url(self) -> str:
        """获取 IDP SLS URL"""
        settings = self.load_settings()
        return settings.get("idp", {}).get("singleLogoutService", {}).get("url", "")

    def get_acs_url(self) -> str:
        """获取 SP ACS URL"""
        settings = self.load_settings()
        return settings.get("sp", {}).get("assertionConsumerService", {}).get("url", "")

    def is_debug_mode(self) -> bool:
        """是否为调试模式"""
        settings = self.load_settings()
        return settings.get("debug", False)

    def is_strict_mode(self) -> bool:
        """是否为严格模式"""
        settings = self.load_settings()
        return settings.get("strict", True)


class SAMLSettings(BaseSettings):
    """
    SAML配置类 - Pydantic Settings集成
    提供环境变量配置和配置文件加载的统一接口

    注意：环境变量名使用大写（如 SAML_SP_ENTITY_ID），属性名使用小写（如 saml_sp_entity_id）
    pydantic-settings 会自动将大写环境变量映射到小写属性名
    """

    # 配置文件路径
    model_config = ConfigDict(
        env_file=None,  # 使用主配置的 env_file，避免重复加载
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # SAML配置文件路径（相对于backend目录）
    saml_settings_file: str = "saml/settings.json"
    saml_advanced_settings_file: str = "saml/advanced_settings.json"

    # SAML SP (Service Provider) 配置
    saml_sp_entity_id: str = "http://localhost:8080/api/v1/auth/metadata"
    saml_acs_url: str = "http://localhost:8080/api/v1/auth/sso/acs"
    saml_sls_url: str = "http://localhost:8080/api/v1/auth/sso/slo"

    # SAML SP 证书（单行格式，换行符用 \n 表示）
    saml_sp_cert: str = ""
    saml_sp_key: str = ""

    # SAML IDP (Identity Provider) 配置
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""
    saml_idp_sls_url: str = ""
    saml_idp_cert: str = ""

    # SAML 安全选项
    saml_strict: bool = True
    saml_debug: bool = False

    # ==================== 便捷方法 ====================

    @property
    def SAML_SP_ENTITY_ID(self) -> str:
        """获取 SP Entity ID（大写别名，用于向后兼容）"""
        return self.saml_sp_entity_id

    @property
    def SAML_ACS_URL(self) -> str:
        """获取 ACS URL（大写别名，用于向后兼容）"""
        return self.saml_acs_url

    @property
    def SAML_SLS_URL(self) -> str:
        """获取 SLS URL（大写别名，用于向后兼容）"""
        return self.saml_sls_url

    @property
    def SAML_SP_CERT(self) -> str:
        """获取 SP 证书（大写别名，用于向后兼容）"""
        return self.saml_sp_cert

    @property
    def SAML_SP_KEY(self) -> str:
        """获取 SP 私钥（大写别名，用于向后兼容）"""
        return self.saml_sp_key

    @property
    def SAML_IDP_ENTITY_ID(self) -> str:
        """获取 IDP Entity ID（大写别名，用于向后兼容）"""
        return self.saml_idp_entity_id

    @property
    def SAML_IDP_SSO_URL(self) -> str:
        """获取 IDP SSO URL（大写别名，用于向后兼容）"""
        return self.saml_idp_sso_url

    @property
    def SAML_IDP_SLS_URL(self) -> str:
        """获取 IDP SLS URL（大写别名，用于向后兼容）"""
        return self.saml_idp_sls_url

    @property
    def SAML_IDP_CERT(self) -> str:
        """获取 IDP 证书（大写别名，用于向后兼容）"""
        return self.saml_idp_cert

    @property
    def SAML_STRICT(self) -> bool:
        """获取严格模式（大写别名，用于向后兼容）"""
        return self.saml_strict

    @property
    def SAML_DEBUG(self) -> bool:
        """获取调试模式（大写别名，用于向后兼容）"""
        return self.saml_debug

    @property
    def SAML_SETTINGS_FILE(self) -> str:
        """获取配置文件路径（大写别名，用于向后兼容）"""
        return self.saml_settings_file

    @property
    def SAML_ADVANCED_SETTINGS_FILE(self) -> str:
        """获取高级配置文件路径（大写别名，用于向后兼容）"""
        return self.saml_advanced_settings_file

    def get_config_loader(self) -> SAMLConfigLoader:
        """
        获取 SAML 配置加载器实例

        Returns:
            SAMLConfigLoader 实例
        """
        return SAMLConfigLoader(
            settings_file=self.saml_settings_file,
            advanced_settings_file=self.saml_advanced_settings_file
        )

    def load_saml_config(self) -> Dict[str, Any]:
        """
        加载完整的 SAML 配置（用于 python3-saml）

        Returns:
            可直接用于 python3-saml 的配置字典
        """
        loader = self.get_config_loader()
        return loader.load_all_settings()

    def create_saml_settings_json(self, output_path: Optional[Path] = None) -> Path:
        """
        从环境变量创建 SAML settings.json 文件

        Args:
            output_path: 输出文件路径，默认为 backend/saml/settings.json

        Returns:
            生成的文件路径
        """
        if output_path is None:
            output_path = get_backend_path() / "saml" / "settings.json"

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建 settings.json 内容
        settings = {
            "strict": self.SAML_STRICT,
            "debug": self.SAML_DEBUG,
            "sp": {
                "entityId": self.SAML_SP_ENTITY_ID,
                "assertionConsumerService": {
                    "url": self.SAML_ACS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": self.SAML_SLS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:transient",
                "x509cert": self.SAML_SP_CERT,
                "privateKey": self.SAML_SP_KEY
            },
            "idp": {
                "entityId": self.SAML_IDP_ENTITY_ID,
                "singleSignOnService": {
                    "url": self.SAML_IDP_SSO_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": self.SAML_IDP_SLS_URL,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": self.SAML_IDP_CERT
            }
        }

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        return output_path


# 全局 SAML 配置实例
def get_saml_settings(**kwargs) -> SAMLSettings:
    """
    获取 SAML 配置实例

    Args:
        **kwargs: 配置项覆盖

    Returns:
        SAMLSettings 实例
    """
    # 应用传入的覆盖参数（会覆盖环境变量和默认值）
    return SAMLSettings(**kwargs)


# 导出全局实例
saml_settings = get_saml_settings()
