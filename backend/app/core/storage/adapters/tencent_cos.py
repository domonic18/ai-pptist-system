"""
腾讯云COS存储适配器
实现BaseStorage接口，提供统一的腾讯云COS存储服务
"""

import asyncio
from datetime import datetime
from functools import partial
from typing import Callable, TypeVar

from app.core.config import settings
from app.core.config.cos_config import get_cos_config, validate_cos_config
from app.core.log_utils import get_logger
from app.core.storage.abc import BaseStorage
from app.core.storage.exceptions import (
    ConfigurationError,
    DownloadError,
    MetadataError,
    StorageError,
    URLError,
    UploadError,
)
from app.core.storage.models import DownloadResult, MetadataResult, UploadResult

logger = get_logger(__name__)

T = TypeVar('T')


class TencentCosAdapter(BaseStorage):
    """
    腾讯云COS存储适配器

    使用腾讯云COS SDK提供对象存储服务，支持：
    - 文件上传/下载
    - 预签名URL生成
    - 文件元数据查询
    """

    # 适配器名称，用于工厂模式注册
    ADAPTER_NAME: str = "tencent_cos"

    def __init__(self) -> None:
        """
        初始化COS存储客户端

        Raises:
            ConfigurationError: 配置不完整时抛出
        """
        self.config = get_cos_config()

        if not validate_cos_config(self.config):
            raise ConfigurationError("腾讯云COS配置不完整，请检查环境变量")

        self._client = self._create_client()

    def _create_client(self):
        """
        创建COS客户端

        Returns:
            CosS3Client: COS客户端实例

        Raises:
            ImportError: SDK未安装时抛出
        """
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as e:
            logger.warning("腾讯云COS SDK未安装")
            raise StorageError(
                "腾讯云COS SDK未安装，请运行: pip install cos-python-sdk-v5",
                code="SDK_NOT_INSTALLED"
            ) from e

        cos_config = CosConfig(
            Region=self.config.region,
            SecretId=self.config.secret_id,
            SecretKey=self.config.secret_key,
            Scheme=self.config.scheme,
            Timeout=self.config.timeout
        )
        return CosS3Client(cos_config)

    async def _run_in_executor(self, func: Callable[..., T], **kwargs) -> T:
        """
        在线程池中运行同步函数

        Args:
            func: 同步函数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        loop = asyncio.get_event_loop()
        bound_func = partial(func, **kwargs)
        return await loop.run_in_executor(None, bound_func)

    async def upload(
        self,
        data: bytes,
        key: str,
        mime_type: str,
        metadata: dict | None = None
    ) -> UploadResult:
        """
        上传文件到COS

        Args:
            data: 文件数据
            key: 存储键
            mime_type: MIME类型
            metadata: 可选的元数据

        Returns:
            UploadResult: 上传结果

        Raises:
            UploadError: 上传失败时抛出
        """
        upload_params = {
            'Bucket': self.config.bucket,
            'Key': key,
            'Body': data,
            'ContentType': mime_type
        }

        if metadata:
            upload_params['Metadata'] = metadata

        # 带重试的上传
        max_retries = self.config.max_retries

        for attempt in range(max_retries + 1):
            try:
                response = await self._run_in_executor(
                    self._client.put_object,
                    **upload_params
                )
                break
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(settings.cos_retry_delay_base * (attempt + 1))
                    continue
                logger.error(
                    "COS上传失败，重试{}次后仍然失败".format(max_retries),
                    extra={'key': key, 'error': str(e)}
                )
                raise UploadError("上传文件失败: {}".format(str(e))) from e

        # 构建访问URL
        access_url = (
            "https://{bucket}."
            "cos.{region}.myqcloud.com/{key}".format(
                bucket=self.config.bucket,
                region=self.config.region,
                key=key
            )
        )

        return UploadResult(
            key=key,
            url=access_url,
            size=len(data),
            mime_type=mime_type,
            bucket=self.config.bucket,
            region=self.config.region,
            etag=response.get('ETag', '').strip('"'),
            uploaded_at=datetime.now()
        )

    async def download(self, key: str) -> DownloadResult:
        """
        从COS下载文件

        Args:
            key: 存储键

        Returns:
            DownloadResult: 下载结果

        Raises:
            DownloadError: 下载失败时抛出
        """
        try:
            response = await self._run_in_executor(
                self._client.get_object,
                Bucket=self.config.bucket,
                Key=key
            )

            data = response['Body'].read()

            return DownloadResult(
                data=data,
                size=len(data),
                mime_type=response.get('ContentType', 'application/octet-stream'),
                last_modified=response.get('LastModified'),
                etag=response.get('ETag', '').strip('"')
            )

        except Exception as e:
            logger.error("COS下载失败", extra={'key': key, 'error': str(e)})
            raise DownloadError("下载文件失败: {}".format(str(e))) from e

    async def delete(self, key: str) -> bool:
        """
        从COS删除文件

        Args:
            key: 存储键

        Returns:
            bool: 删除是否成功

        Raises:
            StorageError: 删除失败时抛出
        """
        try:
            await self._run_in_executor(
                self._client.delete_object,
                Bucket=self.config.bucket,
                Key=key
            )
            logger.info("COS文件删除成功", extra={'key': key})
            return True

        except Exception as e:
            logger.error("COS删除失败", extra={'key': key, 'error': str(e)})
            raise StorageError("删除文件失败: {}".format(str(e))) from e

    async def generate_url(
        self,
        key: str,
        expires: int = 3600,
        operation: str = "get"
    ) -> str:
        """
        生成预签名访问URL

        Args:
            key: 存储键
            expires: 过期时间（秒）
            operation: 操作类型（get/put）

        Returns:
            str: 预签名URL

        Raises:
            URLError: 生成URL失败时抛出
        """
        method = operation.upper()
        if method not in ("GET", "PUT"):
            raise URLError("不支持的操作类型: {}".format(operation))

        try:
            # 生成预签名URL
            # Params参数可以包含额外的查询参数，这些参数也会被签名
            # 注意：不要在Params中包含response-*参数，以免影响外部访问
            url = await self._run_in_executor(
                self._client.get_presigned_url,
                Method=method,
                Bucket=self.config.bucket,
                Key=key,
                Expired=expires,
                Params={}  # 空的Params，避免限制访问
            )
            
            logger.info(
                "成功生成COS预签名URL",
                extra={
                    'key': key[:50],
                    'expires': expires,
                    'method': method,
                    'url_length': len(url)
                }
            )
            return url

        except Exception as e:
            logger.error(
                "COS生成预签名URL失败",
                extra={'key': key, 'expires': expires, 'error': str(e)}
            )
            raise URLError("生成预签名URL失败: {}".format(str(e))) from e

    async def exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 存储键

        Returns:
            bool: 文件是否存在
        """
        try:
            await self._run_in_executor(
                self._client.head_object,
                Bucket=self.config.bucket,
                Key=key
            )
            return True
        except Exception:
            return False

    async def get_metadata(self, key: str) -> MetadataResult:
        """
        获取文件元数据

        Args:
            key: 存储键

        Returns:
            MetadataResult: 文件元数据

        Raises:
            MetadataError: 获取元数据失败时抛出
        """
        try:
            response = await self._run_in_executor(
                self._client.head_object,
                Bucket=self.config.bucket,
                Key=key
            )

            return MetadataResult(
                content_type=response.get('ContentType', ''),
                content_length=response.get('ContentLength', 0),
                etag=response.get('ETag', '').strip('"'),
                last_modified=response.get('LastModified'),
                metadata=response.get('Metadata', {})
            )

        except Exception as e:
            logger.error("COS获取元数据失败", extra={'key': key, 'error': str(e)})
            raise MetadataError("获取文件元数据失败: {}".format(str(e))) from e


__all__ = ['TencentCosAdapter']
