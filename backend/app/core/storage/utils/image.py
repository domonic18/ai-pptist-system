"""
图片下载工具
提供图片下载相关的工具函数
"""

import io
from typing import Protocol, Tuple

import httpx
from PIL import Image

from app.core.log_utils import get_logger
from app.core.storage.exceptions import DownloadError, HTTPError, NetworkError

logger = get_logger(__name__)


class StorageProtocol(Protocol):
    """
    存储协议类型

    定义存储服务需要实现的接口，用于类型提示。
    """

    async def generate_url(self, key: str, expires: int, operation: str) -> str:
        """
        生成预签名URL

        Args:
            key: 存储键
            expires: 过期时间（秒）
            operation: 操作类型

        Returns:
            str: 预签名URL
        """
        ...


async def download_image_by_key(
    cos_key: str,
    storage: StorageProtocol,
    expires: int = 3600
) -> Tuple[bytes, str]:
    """
    通过COS Key下载图片

    使用预签名URL下载图片，避免直接使用SDK可能导致的权限或数据问题。

    Args:
        cos_key: 图片COS Key（如：ai-generated/ppt/xxx/slide_0.png）
        storage: 存储服务实例
        expires: 预签名URL过期时间（秒），默认3600秒

    Returns:
        Tuple[bytes, str]: (图片数据, 图片格式如'PNG', 'JPEG', 'WEBP')

    Raises:
        DownloadError: 下载失败时抛出

    Example:
        >>> from app.core.storage import get_storage_service
        >>> storage = get_storage_service()
        >>> data, fmt = await download_image_by_key("ai-generated/ppt/123/slide_0.png", storage)
        >>> print(f"Downloaded {len(data)} bytes, format: {fmt}")
    """
    # 生成预签名URL
    presigned_url = await storage.generate_url(cos_key, expires=expires, operation="get")

    logger.info(
        "开始下载图片",
        extra={
            "cos_key": cos_key,
            "url_prefix": presigned_url[:80] + "..."
        }
    )

    try:
        # 使用httpx下载图片
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(presigned_url)
            response.raise_for_status()
            image_data = response.content

        # 验证下载的数据是否有效（尝试打开图片）
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        image_format = image.format or "PNG"
        image.close()

        logger.info(
            "图片下载成功",
            extra={
                "cos_key": cos_key,
                "width": width,
                "height": height,
                "format": image_format,
                "size_bytes": len(image_data)
            }
        )

        return image_data, image_format

    except httpx.HTTPStatusError as e:
        logger.error(
            "图片下载HTTP错误",
            extra={"cos_key": cos_key, "status_code": e.response.status_code}
        )
        raise HTTPError(
            f"图片下载失败 (HTTP {e.response.status_code})",
            status_code=e.response.status_code
        ) from e
    except httpx.RequestError as e:
        logger.error(
            "图片下载网络错误",
            extra={"cos_key": cos_key, "error": str(e)}
        )
        raise NetworkError(f"图片下载失败 (网络错误): {str(e)}") from e
    except Exception as e:
        logger.error(
            "图片下载失败",
            extra={"cos_key": cos_key, "error": str(e)}
        )
        raise DownloadError(f"下载图片失败: {str(e)}") from e


__all__ = ['download_image_by_key']
