"""
腾讯云COS服务模块
处理COS相关的业务逻辑和操作
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


class COSConfig(BaseModel):
    """COS配置数据类"""

    secret_id: str = Field(default="", description="腾讯云COS SecretId")
    secret_key: str = Field(default="", description="腾讯云COS SecretKey")
    region: str = Field(default="ap-beijing", description="COS地域")
    bucket: str = Field(default="", description="COS存储桶名称")
    scheme: str = Field(default="https", description="连接协议")

    timeout: int = Field(default=30, description="连接超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    connection_timeout: int = Field(default=10, description="连接建立超时时间（秒）")

    storage_class: str = Field(default="STANDARD", description="存储类型")
    encryption_algorithm: str = Field(default="AES256", description="加密算法")
    encryption_key_id: Optional[str] = Field(default=None, description="加密密钥ID")

    url_expires: int = Field(default=3600, description="预签名URL过期时间（秒）")
    url_cache_size: int = Field(default=1000, description="URL缓存大小")
    url_cache_ttl: int = Field(default=3600, description="URL缓存过期时间（秒）")

    images_prefix: str = Field(default="images", description="图片存储前缀")
    system_prefix: str = Field(default="system", description="系统文件前缀")
    temp_prefix: str = Field(default="temp", description="临时文件前缀")

    public_read: bool = Field(default=False, description="是否允许公共读取")
    user_isolation: bool = Field(default=True, description="是否启用用户隔离")

    enable_monitoring: bool = Field(default=True, description="是否启用监控")
    log_requests: bool = Field(default=True, description="是否记录请求日志")


def get_cos_config() -> COSConfig:
    """从全局配置获取COS配置"""
    return COSConfig(
        secret_id=settings.cos_secret_id,
        secret_key=settings.cos_secret_key,
        region=settings.cos_region,
        bucket=settings.cos_bucket,
        scheme=settings.cos_scheme,
        timeout=settings.cos_timeout,
        max_retries=settings.cos_max_retries,
        connection_timeout=settings.cos_connection_timeout,
        storage_class=settings.cos_storage_class,
        encryption_algorithm=settings.cos_encryption_algorithm,
        encryption_key_id=settings.cos_encryption_key_id,
        url_expires=settings.cos_url_expires,
        url_cache_size=settings.cos_url_cache_size,
        url_cache_ttl=settings.cos_url_cache_ttl,
        images_prefix=settings.cos_images_prefix,
        system_prefix=settings.cos_system_prefix,
        temp_prefix=settings.cos_temp_prefix,
        public_read=settings.cos_public_read,
        user_isolation=settings.cos_user_isolation,
        enable_monitoring=settings.cos_enable_monitoring,
        log_requests=settings.cos_log_requests,
    )


def validate_cos_config(config: COSConfig) -> bool:
    """验证COS配置完整性"""
    required_fields = ["secret_id", "secret_key", "bucket"]

    for field in required_fields:
        if not getattr(config, field):
            return False

    return True


def get_cos_endpoint(config: COSConfig) -> str:
    """构建COS端点URL"""
    return f"{config.bucket}.cos.{config.region}.myqcloud.com"


def get_cos_base_url(config: COSConfig) -> str:
    """构建基础访问URL"""
    return f"{config.scheme}://{get_cos_endpoint(config)}"


def get_encryption_config(config: COSConfig) -> Dict[str, Any]:
    """获取加密配置"""
    if not config.encryption_key_id:
        return {}

    return {
        "ServerSideEncryption": config.encryption_algorithm,
        "SSECustomerKey": config.encryption_key_id
    }


def get_upload_headers(config: COSConfig) -> Dict[str, str]:
    """获取上传头部信息"""
    headers = {}

    # 暂时禁用加密功能，因为配置中的加密密钥ID无效
    # if config.encryption_key_id:
    #     headers.update(get_encryption_config(config))

    return headers


def get_storage_path(config: COSConfig, user_id: str, date_str: str, filename: str) -> str:
    """生成存储路径"""
    return f"{config.images_prefix}/{user_id}/{date_str}/{filename}"


def get_system_path(config: COSConfig, category: str, filename: str) -> str:
    """生成系统文件路径"""
    return f"{config.system_prefix}/{category}/{filename}"


def get_temp_path(config: COSConfig, filename: str) -> str:
    """生成临时文件路径"""
    return f"{config.temp_prefix}/{filename}"


# 全局COS配置实例
cos_config = get_cos_config()
