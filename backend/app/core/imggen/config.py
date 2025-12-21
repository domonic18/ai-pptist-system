"""
图片生成配置管理
统一管理图片生成相关的配置和工具方法
"""

from typing import Tuple, Optional
from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageGenerationConfig:
    """图片生成配置管理类"""

    @staticmethod
    def get_size_mapping(width: int, height: int) -> str:
        """
        根据宽高获取图片尺寸字符串

        Args:
            width: 图片宽度
            height: 图片高度

        Returns:
            str: 尺寸字符串，如 "1024x1024"
        """
        size_map = settings.image_size_mapping

        # 查找匹配的尺寸
        size_string = size_map.get((width, height))

        if size_string:
            logger.debug("找到预定义的图片尺寸", extra={
                "width": width,
                "height": height,
                "size_string": size_string
            })
            return size_string

        # 如果没有找到精确匹配，尝试最接近的尺寸
        closest_size = ImageGenerationConfig._find_closest_size(width, height)
        if closest_size:
            logger.info("使用最接近的图片尺寸", extra={
                "requested": (width, height),
                "closest": closest_size,
                "size_string": size_map[closest_size]
            })
            return size_map[closest_size]

        # 如果还是没有找到，使用默认尺寸
        logger.warning("未找到匹配的图片尺寸，使用默认尺寸", extra={
            "requested": (width, height),
            "default_size": settings.image_default_size
        })
        return settings.image_default_size

    @staticmethod
    def _find_closest_size(width: int, height: int) -> Optional[Tuple[int, int]]:
        """
        查找最接近的预定义尺寸

        Args:
            width: 请求的宽度
            height: 请求的高度

        Returns:
            Optional[Tuple[int, int]]: 最接近的尺寸元组
        """
        size_map = settings.image_size_mapping

        # 计算面积差异
        min_diff = float('inf')
        closest_size = None

        for (w, h) in size_map.keys():
            # 计算面积差异
            diff = abs(w * h - width * height)

            # 计算宽高比差异
            ratio_diff = abs(w / h - width / height) if h > 0 and height > 0 else 0

            # 综合差异（面积差异权重更高）
            total_diff = diff + ratio_diff * 1000

            if total_diff < min_diff:
                min_diff = total_diff
                closest_size = (w, h)

        return closest_size

    @staticmethod
    def get_supported_sizes() -> list:
        """
        获取支持的图片尺寸列表

        Returns:
            list: 支持的尺寸字符串列表
        """
        return list(settings.image_size_mapping.values())

    @staticmethod
    def get_supported_dimensions() -> list:
        """
        获取支持的图片尺寸维度列表

        Returns:
            list: 支持的 (width, height) 元组列表
        """
        return list(settings.image_size_mapping.keys())

    @staticmethod
    def is_valid_quality(quality: str) -> bool:
        """
        检查图片质量是否有效

        Args:
            quality: 图片质量

        Returns:
            bool: 是否有效
        """
        return quality in settings.image_supported_qualities

    @staticmethod
    def get_default_quality() -> str:
        """
        获取默认图片质量

        Returns:
            str: 默认质量
        """
        return settings.image_default_quality

    @staticmethod
    def get_supported_qualities() -> list:
        """
        获取支持的图片质量列表

        Returns:
            list: 支持的质量列表
        """
        return settings.image_supported_qualities.copy()

    @staticmethod
    def normalize_dimensions(width: int, height: int) -> Tuple[int, int]:
        """
        标准化图片尺寸，确保在支持的范围内

        Args:
            width: 原始宽度
            height: 原始高度

        Returns:
            Tuple[int, int]: 标准化后的尺寸
        """
        # 如果尺寸在支持列表中，直接返回
        if (width, height) in settings.image_size_mapping:
            return (width, height)

        # 否则查找最接近的尺寸
        closest = ImageGenerationConfig._find_closest_size(width, height)
        if closest:
            return closest

        # 如果还是没有找到，返回默认尺寸
        return (settings.image_default_width, settings.image_default_height)