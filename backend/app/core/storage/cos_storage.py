"""
腾讯云COS存储适配器
实现BaseStorage接口，提供统一的COS存储服务
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.cos import get_cos_config, validate_cos_config
from app.core.log_utils import get_logger
from .base_storage import BaseStorage, UploadResult, DownloadResult, StorageError

logger = get_logger(__name__)


class COSStorage(BaseStorage):
    """腾讯云COS存储实现"""

    def __init__(self):
        self.config = get_cos_config()
        self.logger = logger

        # 验证配置
        if not validate_cos_config(self.config):
            raise StorageError("COS配置不完整，请检查环境变量", "CONFIG_ERROR")

        # 导入腾讯云SDK（延迟导入，避免启动时错误）
        try:
            from qcloud_cos import CosConfig, CosS3Client
            self._client = self._create_client(CosConfig, CosS3Client)
        except ImportError:
            logger.warning("腾讯云COS SDK未安装，将使用模拟模式")
            self._client = None

    def _create_client(self, CosConfig, CosS3Client):
        """创建COS客户端"""
        cos_config = CosConfig(
            Region=self.config.region,
            SecretId=self.config.secret_id,
            SecretKey=self.config.secret_key,
            Scheme=self.config.scheme,
            Timeout=self.config.timeout
        )
        return CosS3Client(cos_config)

    async def upload(
        self,
        data: bytes,
        key: str,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None
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
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        # 简单重试机制
        max_retries = self.config.max_retries
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # 准备上传参数
                upload_params = {
                    'Bucket': self.config.bucket,
                    'Key': key,
                    'Body': data,
                    'ContentType': mime_type
                }

                # 添加元数据
                if metadata:
                    upload_params['Metadata'] = metadata

                # 执行上传
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.put_object(**upload_params)
                )
                break  # 成功则跳出重试循环

            except Exception as e:
                last_error = e
                if attempt == max_retries:
                    break  # 最后一次尝试失败

                # 简单延迟后重试
                await asyncio.sleep(settings.cos_retry_delay_base * (attempt + 1))
                continue

        # 如果所有重试都失败，抛出错误
        if last_error:
            logger.error(f"COS上传失败，重试{max_retries}次后仍然失败: {str(last_error)}", extra={'key': key})
            raise StorageError(f"上传文件失败: {str(last_error)}", "UPLOAD_ERROR")

        # 构建访问URL
        access_url = (
            f"https://{self.config.bucket}."
            f"cos.{self.config.region}.myqcloud.com/{key}"
        )

        # 构建结果
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
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        try:
            # 执行下载
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.get_object(
                    Bucket=self.config.bucket,
                    Key=key
                )
            )

            # 读取数据
            data = response['Body'].read()

            return DownloadResult(
                data=data,
                size=len(data),
                mime_type=response.get('ContentType', 'application/octet-stream'),
                last_modified=response.get('LastModified'),
                etag=response.get('ETag', '').strip('"')
            )

        except Exception as e:
            logger.error(f"COS下载失败: {str(e)}", extra={'key': key})
            raise StorageError(f"下载文件失败: {str(e)}", "DOWNLOAD_ERROR")

    async def delete(self, key: str) -> bool:
        """
        从COS删除文件

        Args:
            key: 存储键

        Returns:
            bool: 删除是否成功
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        try:
            # 执行删除
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_object(
                    Bucket=self.config.bucket,
                    Key=key
                )
            )

            logger.info(f"COS文件删除成功: {key}")
            return True

        except Exception as e:
            logger.error(f"COS删除失败: {str(e)}", extra={'key': key})
            raise StorageError(f"删除文件失败: {str(e)}", "DELETE_ERROR")

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
            operation: 操作类型（get/put等）

        Returns:
            str: 预签名URL
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        try:
            # 生成预签名URL
            loop = asyncio.get_event_loop()

            if operation.lower() == "get":
                url = await loop.run_in_executor(
                    None,
                    lambda: self._client.get_presigned_url(
                        Method='GET',
                        Bucket=self.config.bucket,
                        Key=key,
                        Expired=expires
                    )
                )
            elif operation.lower() == "put":
                url = await loop.run_in_executor(
                    None,
                    lambda: self._client.get_presigned_url(
                        Method='PUT',
                        Bucket=self.config.bucket,
                        Key=key,
                        Expired=expires
                    )
                )
            else:
                raise StorageError(
                    f"不支持的操作类型: {operation}", "INVALID_OPERATION"
                )

            logger.info(f"成功生成COS预签名URL: {key[:50]}...")
            return url

        except Exception as e:
            logger.error(f"COS生成预签名URL失败: {str(e)}",
                        extra={'key': key, 'expires': expires})
            raise StorageError(f"生成预签名URL失败: {str(e)}", "URL_ERROR")

    async def exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 存储键

        Returns:
            bool: 文件是否存在
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        try:
            # 检查文件是否存在
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.head_object(
                    Bucket=self.config.bucket,
                    Key=key
                )
            )
            return True

        except Exception:
            return False

    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            key: 存储键

        Returns:
            Dict[str, Any]: 文件元数据
        """
        if not self._client:
            raise StorageError("COS客户端未初始化", "CLIENT_ERROR")

        try:
            # 获取文件头信息
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.head_object(
                    Bucket=self.config.bucket,
                    Key=key
                )
            )

            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'etag': response.get('ETag', '').strip('"'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }

        except Exception as e:
            logger.error(f"COS获取元数据失败: {str(e)}", extra={'key': key})
            raise StorageError(f"获取文件元数据失败: {str(e)}", "METADATA_ERROR")

    # 兼容性方法 - 为其他服务提供
    async def delete_image(self, key: str) -> bool:
        """
        删除图片文件（兼容性方法）

        这是对delete方法的包装，为了保持兼容性

        Args:
            key: 存储键

        Returns:
            bool: 删除是否成功
        """
        return await self.delete(key)