"""
存储适配器模块
提供各种对象存储服务的适配器实现
"""

from app.core.storage.adapters.tencent_cos import TencentCosAdapter

# 向后兼容：COSStorage 别名
COSStorage = TencentCosAdapter

__all__ = [
    'TencentCosAdapter',
    'COSStorage',  # 向后兼容
]
