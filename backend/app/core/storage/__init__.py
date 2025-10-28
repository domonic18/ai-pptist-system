"""
存储服务模块
提供统一的存储服务访问接口
"""

from typing import Optional
from app.core.config import settings
from app.core.cos import validate_cos_config
from .base_storage import BaseStorage
from .cos_storage import COSStorage


def get_storage_service() -> BaseStorage:
    """
    获取存储服务实例

    根据配置返回适当的存储服务实例

    Returns:
        BaseStorage: 存储服务实例

    Raises:
        RuntimeError: 当没有可用的存储服务时抛出
    """
    # 优先使用COS存储
    from app.core.cos import get_cos_config, validate_cos_config
    cos_config = get_cos_config()
    if validate_cos_config(cos_config):
        return COSStorage()

    # 如果没有配置任何存储服务，抛出异常
    raise RuntimeError(
        "没有配置可用的存储服务。请配置腾讯云COS或本地文件存储"
    )


# 导出主要类
__all__ = [
    'BaseStorage',
    'COSStorage',
    'get_storage_service'
]