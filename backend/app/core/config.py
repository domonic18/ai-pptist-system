"""
应用配置管理模块
统一管理所有配置信息，包括环境变量和文件配置
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict

from app.utils.config_utils import (
    get_workspace_path, get_backend_path, get_config_path, parse_list_config, parse_json_config
)


class Settings(BaseSettings):
    """应用配置类 - 统一管理所有配置信息"""

    # ==================== 基础配置 ====================
    app_name: str = "AI PPTist"
    app_version: str = "1.0.0"
    app_debug: bool = True
    app_env: str = "development"

    # ==================== API配置 ====================
    api_v1_str: str = "/api/v1"
    project_name: str = "AI PPTist API"

    # ==================== 数据库配置 ====================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "ai_pptist_dev"
    POSTGRES_PASSWORD: str = "dev_password"
    POSTGRES_DB: str = "ai_pptist_dev"
    db_echo: bool = False

    # ==================== Redis配置 ====================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # ==================== 安全配置 ====================
    SECRET_KEY: str = "development-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3600

    # ==================== 文件存储配置 ====================
    upload_dir: str = "uploads"
    export_dir: str = "exports"
    images_dir: str = "images"
    temp_dir: str = "temp"
    log_dir: str = "workspace/log"
    mockdata_dir: str = "app/prompts/mockdata"

    max_upload_size: int = 10485760  # 10MB
    max_image_size: int = 10485760   # 10MB

    allowed_extensions: str = "jpg,jpeg,png,gif,pdf,doc,docx,txt,ppt,pptx"
    image_formats: str = "jpg,jpeg,png,gif,bmp,webp"

    # ==================== COS存储配置 ====================
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_region: str = "ap-beijing"
    cos_bucket: str = ""
    cos_scheme: str = "https"

    cos_timeout: int = 30
    cos_max_retries: int = 3
    cos_connection_timeout: int = 10

    cos_storage_class: str = "STANDARD"
    cos_encryption_algorithm: str = "AES256"
    cos_encryption_key_id: Optional[str] = None

    cos_url_expires: int = 3600
    cos_url_cache_size: int = 1000
    cos_url_cache_ttl: int = 3600

    cos_images_prefix: str = "images"
    cos_system_prefix: str = "system"
    cos_temp_prefix: str = "temp"

    cos_public_read: bool = False
    cos_user_isolation: bool = True

    cos_enable_monitoring: bool = False
    cos_log_requests: bool = False

    # ==================== MetaInsight搜索配置 ====================
    meta_insight_dataset_name: str = "ai-presentations"
    meta_insight_timeout: int = 30
    meta_insight_max_results: int = 100
    meta_insight_default_threshold: int = 50

    # ==================== MLflow配置 ====================
    enable_mlflow: bool = True
    mlflow_tracking_uri: str = "http://localhost:5001"
    mlflow_experiment_name: str = "ai-pptist-experiment"

    # ==================== Mock配置 ====================
    enable_outline_mock: bool = False
    enable_slides_mock: bool = False

    # ==================== 日志配置 ====================
    log_level: str = "INFO"
    log_file: str = "backend.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ==================== 应用服务配置 ====================
    app_port: int = 8080
    app_host: str = "0.0.0.0"

    # ==================== 测试配置 ====================
    test_default_timeout: int = 30
    test_health_check_timeout: int = 2
    test_health_check_interval: int = 1

    # ==================== AI模型默认配置 ====================
    ai_default_temperature: float = 0.7
    ai_default_max_tokens: int = 8192
    ai_default_timeout: int = 240

    # ==================== 图片生成配置 ====================
    # 图片尺寸映射配置 (width, height) -> "size_string"
    image_size_mapping: dict = {
        (1024, 1024): "1024x1024",
        (1792, 1024): "1792x1024",
        (1024, 1792): "1024x1792",
        (512, 512): "512x512",
        (768, 768): "768x768",
        (1024, 768): "1024x768",
        (768, 1024): "768x1024",
        (1024, 576): "1024x576",
        (576, 1024): "576x1024"
    }

    # 默认图片尺寸
    image_default_width: int = 1024
    image_default_height: int = 1024
    image_default_size: str = "1024x1024"

    # 图片质量配置
    image_default_quality: str = "standard"
    image_supported_qualities: list = ["standard", "hd"]

    # ==================== 重试配置 ====================
    cos_retry_delay_base: int = 1
    cos_max_retries: int = 3

    # ==================== Mock服务配置 ====================
    mock_delay_base: float = 0.5
    mock_slide_delay: float = 0.1

    # ==================== CORS配置 ====================
    frontend_url: str = "http://localhost:3005"
    cors_origins: str = '["http://localhost:3005", "http://127.0.0.1:3005"]'

    # ==================== 验证器 ====================
    @field_validator("allowed_extensions")
    @classmethod
    def split_allowed_extensions(cls, value: str) -> List[str]:
        """将允许的文件扩展名字符串转换为列表"""
        return parse_list_config(value)

    @field_validator("image_formats")
    @classmethod
    def split_image_formats(cls, value: str) -> List[str]:
        """将图片格式字符串转换为列表"""
        return parse_list_config(value)

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, value: str) -> List[str]:
        """解析CORS origins配置"""
        return parse_json_config(value)

    # ==================== 计算属性 ====================
    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """构建异步数据库连接URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def absolute_upload_dir(self) -> str:
        """获取绝对上传目录路径"""
        return str(get_workspace_path(self.upload_dir))

    @property
    def absolute_export_dir(self) -> str:
        """获取绝对导出目录路径"""
        return str(get_workspace_path(self.export_dir))

    @property
    def absolute_images_dir(self) -> str:
        """获取绝对图片目录路径"""
        return str(get_workspace_path(self.images_dir))

    @property
    def absolute_temp_dir(self) -> str:
        """获取绝对临时目录路径"""
        return str(get_workspace_path(self.temp_dir))

    @property
    def absolute_log_dir(self) -> str:
        """获取绝对日志目录路径"""
        return str(get_workspace_path(self.log_dir))

    @property
    def absolute_mockdata_dir(self) -> str:
        """获取绝对Mock数据目录路径"""
        return str(get_backend_path(self.mockdata_dir))

    @property
    def workspace_dir(self) -> str:
        """获取workspace目录路径"""
        return str(get_workspace_path())

    @property
    def cos_enabled(self) -> bool:
        """检查COS是否启用"""
        return bool(self.cos_secret_id and self.cos_secret_key and self.cos_bucket)

    @property
    def absolute_log_file(self) -> str:
        """获取绝对日志文件路径"""
        return str(get_workspace_path(self.log_dir) / self.log_file)

    model_config = ConfigDict(
        env_file=get_config_path(".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        validate_default=True
    )


def get_settings() -> Settings:
    """获取应用配置实例"""
    # 环境变量文件加载由外部环境控制（Docker Compose、launch.json等）
    # 这里只返回配置实例，不主动加载环境文件
    return Settings()


# 全局配置实例
settings = get_settings()
