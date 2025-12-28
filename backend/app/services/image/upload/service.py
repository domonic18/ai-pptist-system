"""
图片上传服务
处理用户上传图片的业务逻辑
"""

import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.schemas.image_manager import ImageCreate
from app.core.storage import get_storage_service
from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageUploadService:
    """图片上传服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ImageRepository(db)
        self.storage_service = get_storage_service()

    async def upload_user_image(
        self,
        file: UploadFile,
        user_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传用户图片"""
        try:
            logger.info(
                "开始上传用户图片",
                extra={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "user_id": user_id
                }
            )

            # 验证文件类型
            if not self._validate_file_type(file.content_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不支持的文件类型，仅支持图片文件"
                )

            # 读取文件内容
            file_content = await file.read()

            # 验证文件大小
            if len(file_content) > settings.max_image_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"文件大小超过限制: {len(file_content)} > {settings.max_image_size}"
                )

            # 生成COS存储路径
            cos_key = self._generate_storage_key(file.filename, user_id)

            # 上传到COS
            upload_result = await self.storage_service.upload(
                file_content, cos_key, file.content_type
            )

            # 创建图片记录
            image_data = ImageCreate(
                original_filename=file.filename,
                file_size=len(file_content),
                mime_type=file.content_type,
                description=description,
                tags=[],
                is_public=False,
                image_url=upload_result.url,
                cos_key=cos_key,
                cos_bucket=settings.cos_bucket,
                cos_region=settings.cos_region,
                source_type="uploaded"
            )

            image = await self.repository.create_image(image_data, user_id)

            logger.info(
                "用户图片上传成功",
                extra={
                    "image_id": image.id,
                    "cos_key": cos_key,
                    "file_size": len(file_content)
                }
            )

            return {
                "success": True,
                "image_id": image.id,
                "url": upload_result.url,
                "cos_key": cos_key,
                "message": "图片上传成功"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"图片上传失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"图片上传失败: {str(e)}"
            )

    async def generate_presigned_upload_url(
        self,
        filename: str,
        content_type: str,
        user_id: str
    ) -> Dict[str, Any]:
        """生成预签名上传URL"""
        try:
            # 验证文件类型
            if not self._validate_file_type(content_type):
                raise ValueError("不支持的文件类型")

            # 生成COS存储路径
            cos_key = self._generate_storage_key(filename, user_id)

            # 生成预签名URL
            presigned_url = await self.storage_service.generate_url(
                cos_key, settings.cos_url_expires, "put"
            )

            # 创建临时的数据库记录
            image_data = ImageCreate(
                original_filename=filename,
                file_size=0,  # 文件大小将在上传后更新
                mime_type=content_type,
                is_public=False,
                cos_key=cos_key,
                cos_bucket=settings.cos_bucket,
                cos_region=settings.cos_region,
                source_type="uploaded",
                storage_status="uploading"
            )

            image = await self.repository.create_image(image_data, user_id)

            # 构建访问URL
            access_url = f"https://{settings.cos_bucket}.cos.{settings.cos_region}.myqcloud.com/{cos_key}"

            return {
                "success": True,
                "upload_url": presigned_url,
                "cos_key": cos_key,
                "access_url": access_url,
                "image_id": image.id,
                "expires_in": settings.cos_url_expires,
                "message": "预签名URL生成成功"
            }

        except Exception as e:
            logger.error(f"生成预签名URL失败: {e}")
            return {
                "success": False,
                "message": f"生成预签名URL失败: {str(e)}",
                "error": str(e)
            }

    async def confirm_upload(
        self,
        image_id: str,
        user_id: str,
        file_size: int
    ) -> Dict[str, Any]:
        """确认上传完成"""
        try:
            # 获取图片记录
            image = await self.repository.get_image_by_id(image_id)
            if not image or image.user_id != user_id:
                raise ValueError("图片记录不存在或权限不足")

            # 验证文件是否存在
            if not await self.storage_service.exists(image.cos_key):
                raise ValueError("COS文件不存在")

            # 更新数据库记录
            update_data = {
                "file_size": file_size,
                "storage_status": "active"
            }

            await self.repository.update_image(image_id, update_data)

            return {
                "success": True,
                "image_id": image_id,
                "message": "上传确认成功"
            }

        except Exception as e:
            logger.error(f"上传确认失败: {e}")
            return {
                "success": False,
                "message": f"上传确认失败: {str(e)}",
                "error": str(e)
            }

    def _validate_file_type(self, content_type: str) -> bool:
        """验证文件类型是否为支持的图片格式"""
        from app.core.config import settings
        return content_type in settings.supported_image_mime_types

    def _generate_storage_key(self, filename: str, user_id: str) -> str:
        """生成存储对象键"""
        # 生成唯一文件名
        file_ext = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4()}{file_ext}"

        # 构建存储键（保持与原有COS键格式兼容）
        return f"images/{user_id}/{unique_name}"