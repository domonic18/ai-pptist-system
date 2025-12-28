"""
图片上传业务处理器
处理复杂的上传业务逻辑，支持单个和批量上传
"""

import asyncio
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.upload.service import ImageUploadService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageUploadHandler:
    """图片上传业务处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_service = ImageUploadService(db)

    async def handle_single_upload(
        self,
        file: UploadFile,
        user_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理单个文件上传"""
        try:
            logger.info(
                "处理单个文件上传",
                extra={
                    "filename": file.filename,
                    "user_id": user_id
                }
            )

            # 执行上传
            upload_result = await self.upload_service.upload_user_image(
                file=file,
                user_id=user_id,
                description=description
            )

            if not upload_result["success"]:
                error_message = upload_result.get('message', '未知错误')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"图片上传失败: {error_message}"
                )

            logger.info(
                "单个文件上传成功",
                extra={
                    "image_id": upload_result["image_id"],
                    "filename": file.filename
                }
            )

            return upload_result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "单个文件上传失败",
                extra={
                    "filename": file.filename,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"图片上传失败: {str(e)}"
            ) from e

    async def handle_batch_upload(
        self,
        files: List[UploadFile],
        user_id: str
    ) -> Dict[str, Any]:
        """处理批量文件上传"""
        try:
            logger.info(
                "处理批量文件上传",
                extra={
                    "file_count": len(files),
                    "user_id": user_id
                }
            )

            successful_uploads = []
            failed_uploads = []

            # 处理每个文件
            for file in files:
                try:
                    # 重置文件指针位置（重要：并发上传时需要重置）
                    await file.seek(0)

                    # 执行单个文件上传
                    upload_result = await self.upload_service.upload_user_image(
                        file=file,
                        user_id=user_id
                    )

                    if upload_result["success"]:
                        successful_uploads.append({
                            "filename": file.filename,
                            "image_id": upload_result["image_id"],
                            "url": upload_result["url"]
                        })
                    else:
                        failed_uploads.append({
                            "filename": file.filename,
                            "error": upload_result["message"]
                        })

                except Exception as e:
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": str(e)
                    })

            logger.info(
                "批量文件上传完成",
                extra={
                    "successful": len(successful_uploads),
                    "failed": len(failed_uploads)
                }
            )

            return {
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "summary": {
                    "total": len(files),
                    "successful": len(successful_uploads),
                    "failed": len(failed_uploads)
                }
            }

        except Exception as e:
            logger.error(
                "批量文件上传失败",
                extra={
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"批量图片上传失败: {str(e)}"
            ) from e

    async def handle_presigned_upload(
        self,
        filename: str,
        content_type: str,
        user_id: str
    ) -> Dict[str, Any]:
        """处理预签名上传"""
        try:
            logger.info(
                "处理预签名上传",
                extra={
                    "filename": filename,
                    "user_id": user_id
                }
            )

            # 生成预签名URL
            presigned_result = await self.upload_service.generate_presigned_upload_url(
                filename=filename,
                content_type=content_type,
                user_id=user_id
            )

            if not presigned_result["success"]:
                error_message = presigned_result.get('message', '未知错误')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"生成预签名URL失败: {error_message}"
                )

            logger.info(
                "预签名URL生成成功",
                extra={
                    "filename": filename,
                    "image_id": presigned_result["image_id"]
                }
            )

            return presigned_result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "预签名URL生成失败",
                extra={
                    "filename": filename,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"生成预签名URL失败: {str(e)}"
            ) from e