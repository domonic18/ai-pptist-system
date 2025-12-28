"""
图片上传API端点 - 重构版本
专门处理用户图片上传相关的操作
采用薄路由、重服务的架构设计
"""

from fastapi import APIRouter, Depends, File, UploadFile, Form
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.upload.handler import ImageUploadHandler
from app.schemas.image_upload import PresignedUrlRequest
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["图片上传"])


@router.post(
    "",
    response_model=StandardResponse,
    summary="用户上传图片",
    description="用户上传图片 - 创建数据库记录并上传到COS"
)
async def upload_image(
    file: UploadFile = File(..., description="要上传的图片文件"),
    description: Optional[str] = Form(None, description="图片描述或提示词"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    用户上传图片 - 创建数据库记录并上传到COS

    功能流程：
    1. 验证文件格式和大小
    2. 上传到COS存储
    3. 创建数据库记录
    4. 返回图片信息
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理上传逻辑
    handler = ImageUploadHandler(db)
    upload_result = await handler.handle_single_upload(
        file=file,
        user_id=user_id,
        description=description
    )

    # 返回统一的标准化响应格式
    return StandardResponse(
        status="success" if upload_result["success"] else "error",
        message=upload_result["message"],
        data={
            "success": upload_result["success"],
            "image_id": upload_result["image_id"],
            "image_url": upload_result["url"],
            "cos_key": upload_result.get("cos_key", "")
        }
    )


@router.post(
    "/presigned",
    response_model=StandardResponse,
    summary="获取预签名上传URL",
    description="生成COS预签名上传URL，用于前端直接上传"
)
async def get_presigned_upload_url(
    request: PresignedUrlRequest,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取COS预签名上传URL

    功能流程：
    1. 验证文件信息
    2. 生成COS对象键
    3. 创建预签名上传URL
    4. 返回URL和相关信息
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理预签名URL生成
    handler = ImageUploadHandler(db)
    presigned_result = await handler.handle_presigned_upload(
        filename=request.filename,
        content_type=request.content_type,
        user_id=user_id
    )

    if not presigned_result["success"]:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=presigned_result["message"]
        )

    return StandardResponse(
        status="success" if presigned_result["success"] else "error",
        message=presigned_result["message"],
        data={
            "success": presigned_result["success"],
            "upload_url": presigned_result["upload_url"],
            "cos_key": presigned_result["cos_key"],
            "access_url": presigned_result["access_url"],
            "expires_in": presigned_result["expires_in"]
        }
    )


@router.post(
    "/batch",
    response_model=StandardResponse,
    summary="批量上传图片",
    description="批量上传多张图片，支持并发处理和详细的错误报告"
)
async def batch_upload_images(
    files: List[UploadFile] = File(..., description="要上传的图片文件列表"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    批量上传图片

    功能流程：
    1. 验证所有文件格式和大小
    2. 并发上传到COS存储
    3. 批量创建数据库记录
    4. 返回详细的处理结果
    """
    # TODO: 从认证中获取用户ID（暂时使用固定值）
    user_id = "demo_001"

    # 使用业务处理器处理批量上传逻辑
    handler = ImageUploadHandler(db)
    batch_result = await handler.handle_batch_upload(
        files=files,
        user_id=user_id
    )

    # 返回标准响应
    return StandardResponse(
        status="success",
        message=f"批量上传完成，成功: {batch_result['summary']['successful']}，失败: {batch_result['summary']['failed']}",
        data=batch_result
    )