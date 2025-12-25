"""
存储适配器工厂
提供适配器注册和创建功能
"""

from typing import Callable, Dict, Type

from app.core.log_utils import get_logger
from app.core.storage.abc import BaseStorage
from app.core.storage.exceptions import ConfigurationError

logger = get_logger(__name__)

# 适配器注册表
_adapter_registry: Dict[str, Type[BaseStorage]] = {}


def register_adapter(name: str, adapter_class: Type[BaseStorage]) -> None:
    """
    注册存储适配器

    Args:
        name: 适配器名称（如 'tencent_cos', 'aliyun_oss', 'aws_s3'）
        adapter_class: 适配器类

    Example:
        >>> register_adapter('tencent_cos', TencentCosAdapter)
    """
    _adapter_registry[name] = adapter_class
    logger.info("已注册存储适配器", extra={'adapter': name})


def get_adapter_class(name: str) -> Type[BaseStorage]:
    """
    获取适配器类

    Args:
        name: 适配器名称

    Returns:
        Type[BaseStorage]: 适配器类

    Raises:
        ConfigurationError: 适配器不存在时抛出
    """
    adapter_class = _adapter_registry.get(name)
    if not adapter_class:
        available = ', '.join(_adapter_registry.keys())
        raise ConfigurationError(
            "存储适配器 '{}' 不存在，可用适配器: {}".format(name, available)
        )
    return adapter_class


def create_adapter(name: str) -> BaseStorage:
    """
    创建适配器实例

    Args:
        name: 适配器名称

    Returns:
        BaseStorage: 适配器实例

    Raises:
        ConfigurationError: 适配器不存在或创建失败时抛出
    """
    try:
        adapter_class = get_adapter_class(name)
        return adapter_class()
    except Exception as e:
        logger.error("创建存储适配器失败", extra={'adapter': name, 'error': str(e)})
        raise ConfigurationError(
            "创建存储适配器 '{}' 失败: {}".format(name, str(e))
        ) from e


def list_available_adapters() -> list[str]:
    """
    列出所有已注册的适配器

    Returns:
        list[str]: 适配器名称列表
    """
    return list(_adapter_registry.keys())


__all__ = [
    'register_adapter',
    'get_adapter_class',
    'create_adapter',
    'list_available_adapters',
]
