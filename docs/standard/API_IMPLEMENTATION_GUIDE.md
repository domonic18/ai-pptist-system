# API 实现指南

## 1. 概述

本文档提供具体的 API 实现指导和代码示例，帮助开发人员快速实现符合规范的 API 端点。

## 2. 项目结构

### 2.1 后端项目结构
```
app/
├── api/
│   ├── v1/                    # API 版本 1
│   │   ├── endpoints/         # 端点实现
│   │   │   ├── images.py      # 图片管理
│   │   │   ├── image_upload.py # 图片上传
│   │   │   ├── image_search.py # 图片搜索
│   │   │   └── __init__.py
│   │   ├── router.py          # 路由聚合
│   │   └── __init__.py
│   └── __init__.py
├── schemas/                   # Pydantic 模型
│   ├── common.py              # 通用响应模型
│   ├── image.py               # 图片模型
│   ├── image_upload.py        # 图片上传模型
│   ├── image_search.py        # 图片搜索模型
│   └── __init__.py
├── services/                  # 业务服务
│   ├── image/
│   │   ├── upload_service.py  # 上传服务
│   │   ├── search_service.py  # 搜索服务
│   │   └── __init__.py
│   └── __init__.py
└── core/                      # 核心功能
    ├── deps.py               # 依赖注入
    ├── logging.py            # 日志配置
    └── __init__.py
```

## 3. 依赖注入配置

### 3.1 核心依赖 (core/deps.py)
```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generator, Optional

from app.db.session import async_session
from app.models.user import User
from app.services.auth import get_current_user

# 数据库会话依赖
def get_db() -> Generator[AsyncSession, None, None]:
    """获取数据库会话"""
    try:
        db = async_session()
        yield db
    finally:
        await db.close()

# 当前用户依赖
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前认证用户"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )
        user = await user_service.get_user_by_id(db, user_id=user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )
```

## 4. 通用响应模型

### 4.1 标准响应模型 (schemas/common.py)
```python
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from enum import Enum

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

class StandardResponse(BaseModel):
    """标准响应格式"""
    status: ResponseStatus = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="时间戳")
    request_id: str = Field(..., description="请求ID")

class SuccessResponse(StandardResponse):
    """成功响应"""
    def __init__(self, message: str, data: Any = None, **kwargs):
        super().__init__(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            **kwargs
        )

class ErrorResponse(StandardResponse):
    """错误响应"""
    def __init__(self, message: str, error_code: str, error_details: Dict[str, Any] = None, **kwargs):
        super().__init__(
            status=ResponseStatus.ERROR,
            message=message,
            error_code=error_code,
            error_details=error_details or {},
            **kwargs
        )
```

## 5. 业务模型定义

### 5.1 图片模型 (schemas/image.py)
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ImageBase(BaseModel):
    """图片基础模型"""
    prompt: str = Field(..., description="生成提示词")
    model_name: str = Field(..., description="模型名称")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")

class ImageCreate(ImageBase):
    """图片创建模型"""
    user_id: str = Field(..., description="用户ID")
    cos_key: str = Field(..., description="COS对象键")

class ImageResponse(ImageBase):
    """图片响应模型"""
    id: str = Field(..., description="图片ID")
    url: str = Field(..., description="图片URL")
    file_size: int = Field(..., description="文件大小")
    mime_type: str = Field(..., description="MIME类型")
    created_at: datetime = Field(..., description="创建时间")
    user_id: str = Field(..., description="用户ID")

    class Config:
        from_attributes = True
```

## 6. 端点实现示例

### 6.1 图片列表端点 (endpoints/images.py)
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import SuccessResponse, PaginationRequest
from app.schemas.image import ImageResponse
from app.services.image import image_service

router = APIRouter(tags=["Image Management"])

@router.get(
    "",
    response_model=SuccessResponse,
    summary="获取图片列表",
    description="分页获取当前用户的图片列表"
)
async def list_images(
    pagination: PaginationRequest = Depends(),
    search: Optional[str] = None,
    image_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse:
    """
    获取图片列表

    Args:
        pagination: 分页参数
        search: 搜索关键词
        image_type: 图片类型过滤
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 包含图片列表的响应
    """
    # 调用服务层获取数据
    images, total = await image_service.list_images(
        db=db,
        user_id=str(current_user.id),
        skip=pagination.skip,
        limit=pagination.limit,
        search=search,
        image_type=image_type
    )

    # 构建分页信息
    pagination_data = {
        "total": total,
        "skip": pagination.skip,
        "limit": pagination.limit,
        "has_next": pagination.skip + pagination.limit < total,
        "has_prev": pagination.skip > 0
    }

    # 返回标准化响应
    return SuccessResponse(
        message="图片列表获取成功",
        data={
            "items": [ImageResponse.from_orm(image) for image in images],
            "pagination": pagination_data
        }
    )
```

### 6.2 图片详情端点
```python
@router.get(
    "/{image_id}",
    response_model=SuccessResponse,
    summary="获取图片详情",
    description="根据ID获取图片详细信息"
)
async def get_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse:
    """
    获取图片详情

    Args:
        image_id: 图片ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 包含图片详情的响应
    """
    # 调用服务层获取图片
    image = await image_service.get_image(
        db=db,
        image_id=image_id,
        user_id=str(current_user.id)
    )

    if not image:
        from app.schemas.common import ErrorResponse
        return ErrorResponse(
            message="图片不存在",
            error_code="IMAGE_NOT_FOUND"
        )

    # 返回标准化响应
    return SuccessResponse(
        message="图片详情获取成功",
        data=ImageResponse.from_orm(image)
    )
```

## 7. 图片上传实现

### 7.1 上传模型 (schemas/image_upload.py)
```python
from pydantic import BaseModel, Field
from typing import Optional

class ImageUploadResponse(BaseModel):
    """图片上传响应"""
    success: bool = Field(..., description="上传是否成功")
    image_id: str = Field(..., description="图片ID")
    image_url: str = Field(..., description="图片访问URL")
    cos_key: str = Field(..., description="COS对象键")
    message: str = Field(..., description="响应消息")

class PresignedUrlRequest(BaseModel):
    """预签名URL请求"""
    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="文件类型")

class PresignedUrlResponse(BaseModel):
    """预签名URL响应"""
    success: bool = Field(..., description="生成是否成功")
    upload_url: str = Field(..., description="上传URL")
    download_url: str = Field(..., description="下载URL")
    cos_key: str = Field(..., description="COS对象键")
    expires_at: str = Field(..., description="过期时间")
```

### 7.2 上传端点 (endpoints/image_upload.py)
```python
from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.image_upload import ImageUploadResponse, PresignedUrlRequest, PresignedUrlResponse
from app.services.image.upload_service import image_upload_service

router = APIRouter(tags=["Image Upload"])

@router.post(
    "/",
    response_model=ImageUploadResponse,
    summary="上传图片",
    description="上传图片文件到服务器"
)
async def upload_image(
    file: UploadFile = File(..., description="图片文件"),
    description: Optional[str] = Form(None, description="图片描述"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ImageUploadResponse:
    """
    上传图片

    Args:
        file: 上传的文件
        description: 图片描述
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ImageUploadResponse: 上传结果
    """
    # 调用上传服务
    result = await image_upload_service.upload_image(
        db=db,
        file=file,
        user_id=str(current_user.id),
        description=description
    )

    return ImageUploadResponse(**result)

@router.post(
    "/presigned",
    response_model=PresignedUrlResponse,
    summary="获取预签名URL",
    description="生成用于前端直传的预签名URL"
)
async def get_presigned_url(
    request: PresignedUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PresignedUrlResponse:
    """
    获取预签名上传URL

    Args:
        request: 预签名URL请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        PresignedUrlResponse: 预签名URL信息
    """
    # 调用服务生成预签名URL
    result = await image_upload_service.generate_presigned_url(
        db=db,
        filename=request.filename,
        content_type=request.content_type,
        user_id=str(current_user.id)
    )

    return PresignedUrlResponse(**result)
```

## 8. 图片搜索实现

### 8.1 搜索模型 (schemas/image_search.py)
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class ImageSearchRequest(BaseModel):
    """图片搜索请求"""
    prompt: str = Field(..., description="搜索提示词")
    limit: int = Field(10, description="返回数量限制")
    match_threshold: float = Field(0.7, description="匹配阈值")

class ImageSearchResult(BaseModel):
    """图片搜索结果"""
    id: str = Field(..., description="图片ID")
    prompt: str = Field(..., description="生成提示词")
    url: str = Field(..., description="图片URL")
    similarity: float = Field(..., description="相似度得分")
    match_type: str = Field(..., description="匹配类型")

class ImageSearchResponse(BaseModel):
    """图片搜索响应"""
    success: bool = Field(..., description="搜索是否成功")
    results: List[ImageSearchResult] = Field(..., description="搜索结果")
    total: int = Field(..., description="结果总数")
    message: str = Field(..., description="响应消息")
```

### 8.2 搜索端点 (endpoints/image_search.py)
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.image_search import ImageSearchRequest, ImageSearchResponse
from app.services.image.search_service import image_search_service

router = APIRouter(tags=["Image Search"])

@router.post(
    "/",
    response_model=ImageSearchResponse,
    summary="搜索图片",
    description="根据提示词搜索相关图片"
)
async def search_images(
    request: ImageSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ImageSearchResponse:
    """
    搜索图片

    Args:
        request: 搜索请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        ImageSearchResponse: 搜索结果
    """
    # 调用搜索服务
    result = await image_search_service.search_images(
        db=db,
        prompt=request.prompt,
        user_id=str(current_user.id),
        limit=request.limit,
        match_threshold=request.match_threshold
    )

    return ImageSearchResponse(**result)
```

## 9. 路由聚合配置

### 9.1 路由聚合 (router.py)
```python
from fastapi import APIRouter

from app.api.v1.endpoints import images, image_upload, image_search

# 创建API路由器
api_router = APIRouter()

# 注册各个模块的路由
api_router.include_router(images.router, prefix="/images", tags=["图片管理"])
api_router.include_router(image_upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(image_search.router, prefix="/images/search", tags=["图片搜索"])

# 健康检查端点
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

## 10. 错误处理中间件

### 10.1 全局异常处理
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorResponse

app = FastAPI()

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="服务器内部错误",
            error_code="INTERNAL_ERROR",
            request_id=request.state.request_id
        ).dict()
    )

# 请求验证错误处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            message="请求参数验证失败",
            error_code="VALIDATION_ERROR",
            error_details={"errors": exc.errors()},
            request_id=request.state.request_id
        ).dict()
    )

# HTTP异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=request.state.request_id
        ).dict()
    )
```

## 11. 测试示例

### 11.1 单元测试示例
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas.common import SuccessResponse

client = TestClient(app)

@pytest.mark.asyncio
async def test_list_images():
    """测试获取图片列表"""
    # Mock 服务层
    with patch('app.services.image.image_service.list_images') as mock_service:
        mock_service.return_value = ([], 0)

        # 发送请求
        response = client.get("/api/v1/images", headers={"Authorization": "Bearer test-token"})

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "图片列表获取成功"
        assert "items" in data["data"]
        assert "pagination" in data["data"]
```

## 12. 部署配置

### 12.1 CORS 配置
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 12.2 速率限制配置
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 应用速率限制
@app.get("/images")
@limiter.limit("100/minute")
async def list_images(request: Request):
    pass
```

## 13. 性能优化

### 13.1 数据库查询优化
```python
# 使用 selectinload 避免 N+1 查询
from sqlalchemy.orm import selectinload

async def get_user_with_images(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(User).options(selectinload(User.images)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

### 13.2 缓存优化
```python
from aiocache import cached

@cached(ttl=300)  # 缓存5分钟
async def get_image(image_id: str, db: AsyncSession):
    # 数据库查询
    pass
```

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效