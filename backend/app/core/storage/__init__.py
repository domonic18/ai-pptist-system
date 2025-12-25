"""
存储服务模块
提供统一的存储服务访问接口，支持多种存储适配器
"""

from app.core.config.cos_config import get_cos_config, validate_cos_config
from app.core.storage.abc import BaseStorage
from app.core.storage.adapters.tencent_cos import TencentCosAdapter
from app.core.storage.exceptions import *
from app.core.storage.factory import (
    create_adapter,
    list_available_adapters,
    register_adapter,
)
from app.core.storage.models import *
from app.core.storage.utils import download_image_by_key

# 自动注册腾讯云COS适配器
register_adapter(TencentCosAdapter.ADAPTER_NAME, TencentCosAdapter)


def get_storage_service(adapter_name: str | None = None) -> BaseStorage:
    """
    获取存储服务实例

    Args:
        adapter_name: 适配器名称（如 'tencent_cos'），不指定则自动检测

    Returns:
        BaseStorage: 存储服务实例

    Raises:
        RuntimeError: 当没有可用的存储服务时抛出

    Example:
        >>> # 自动检测
        >>> storage = get_storage_service()
        >>> # 指定适配器
        >>> storage = get_storage_service('tencent_cos')
    """
    # 如果未指定适配器，自动检测可用的
    if adapter_name is None:
        cos_config = get_cos_config()
        if validate_cos_config(cos_config):
            adapter_name = TencentCosAdapter.ADAPTER_NAME
        else:
            raise RuntimeError(
                "没有可用的存储服务。请配置腾讯云COS存储"
            )

    return create_adapter(adapter_name)


# 向后兼容的别名
COSStorage = TencentCosAdapter


__all__ = [
    # 工厂函数
    'get_storage_service',
    'create_adapter',
    'list_available_adapters',
    'register_adapter',
    # 抽象接口
    'BaseStorage',
    # 适配器类
    'TencentCosAdapter',
    'COSStorage',  # 向后兼容
    # 工具函数
    'download_image_by_key',
]
