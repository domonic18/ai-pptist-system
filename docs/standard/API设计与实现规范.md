# API 设计与实现规范

## 1. 概述

本文档是 AI PPTist 项目的统一 API 设计与实现规范，基于当前项目的分层架构和最佳实践。所有新开发的 API 必须遵循此规范。

## 2. 设计原则

### 2.1 RESTful 原则
- **资源导向**: 使用名词表示资源，动词表示操作
- **无状态**: 每个请求包含所有必要信息
- **统一接口**: 使用标准 HTTP 方法和状态码
- **可缓存**: 支持适当的缓存策略

### 2.2 分层架构原则
- **轻路由**: 路由层只负责请求分发和响应格式化
- **重服务**: 业务逻辑集中在服务层实现
- **职责分离**: handler 处理网络层，service 处理业务层
- **模块化**: 按功能模块组织代码结构

### 2.3 一致性原则
- 命名约定统一
- 响应格式标准化
- 错误处理一致
- 版本管理规范

## 3. 项目结构规范

### 3.1 后端项目结构
```
app/
├── api/
│   ├── v1/                    # API 版本目录
│   │   ├── endpoints/         # 端点实现（轻路由）
│   │   │   ├── images.py      # 图片管理端点
│   │   │   ├── tags.py        # 标签管理端点
│   │   │   └── generation.py  # AI生成端点
│   │   └── router.py          # 路由聚合配置
├── services/                  # 业务服务层（重服务）
│   ├── image/
│   │   ├── management_handler.py  # 图片管理处理器
│   │   ├── management_service.py  # 图片管理服务
│   │   ├── tag_handler.py         # 标签处理器
│   │   └── tag_service.py         # 标签服务
├── schemas/                   # Pydantic 数据模型
│   ├── common.py              # 通用响应模型
│   ├── image_manager.py       # 图片管理模型
│   └── tag.py                 # 标签模型
├── repositories/              # 数据访问层
│   ├── base.py                # 基础仓库类
│   ├── image.py               # 图片仓库
│   └── tag.py                 # 标签仓库
└── models/                    # 数据库模型
    ├── image.py               # 图片模型
    └── tag.py                 # 标签模型
```

### 3.2 分层职责说明

#### 端点层 (endpoints/)
- 处理 HTTP 请求和响应
- 参数验证和序列化
- 调用对应的 handler
- 返回标准化的响应

#### 处理器层 (handler/)
- 处理网络层逻辑
- 日志记录和异常处理
- 调用对应的 service
- 数据转换和格式化

#### 服务层 (service/)
- 实现核心业务逻辑
- 数据验证和处理
- 调用仓库层进行数据操作
- 业务规则和流程控制

## 4. 路由管理规范

### 4.1 路由文件结构

#### 端点文件内部 (如 tags.py)
```python
# ✅ 正确：使用相对路径（不以/开头）
router = APIRouter(tags=["Tags"])

@router.get("", summary="获取标签列表")  # 根路径使用空字符串
@router.get("/{tag_name}", summary="获取标签详情")  # 参数路径使用/开头
@router.post("", summary="创建标签")  # POST操作使用空字符串
```

#### 路由聚合文件 (router.py)
```python
# ✅ 正确：统一在聚合文件中管理前缀
api_router = APIRouter()

# 注册各模块路由 - 统一前缀管理
api_router.include_router(image_manager.router, prefix="/images", tags=["图片管理"])
api_router.include_router(tags.router, prefix="/tags", tags=["标签管理"])
api_router.include_router(generation.router, prefix="/generate", tags=["AI Generation"])
```

### 4.2 API路径示例
```
# 图片管理
GET    /api/v1/images           # 获取图片列表
GET    /api/v1/images/{id}     # 获取图片详情
DELETE /api/v1/images/{id}     # 删除图片

# 标签管理
GET    /api/v1/tags            # 获取标签列表
POST   /api/v1/tags            # 创建标签
DELETE /api/v1/tags/{name}     # 删除标签

# AI生成
POST   /api/v1/generate/outline # 生成大纲
POST   /api/v1/generate/slides  # 生成幻灯片
```

### 4.3 命名约定
- 使用复数名词表示资源集合：`/images` 而不是 `/image`
- 使用连字符分隔单词：`search-statistics` 而不是 `searchStatistics`
- 保持 URL 小写
- 版本前缀：`/api/v1/`

## 5. 端点实现规范

### 5.1 端点层实现示例
```python
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.image.tag_handler import TagHandler
from app.schemas.tag import TagCreate, TagSearchParams
from app.schemas.common import StandardResponse
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Tags"])

@router.get(
    "",
    response_model=StandardResponse,
    summary="获取标签列表",
    description="获取所有标签，支持搜索和分页"
)
async def get_all_tags(
    query: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    sort_by: str = Query("usage_count", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取标签列表

    Args:
        query: 搜索关键词
        page: 页码
        limit: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向
        db: 数据库会话

    Returns:
        StandardResponse: 包含标签列表的响应
    """
    try:
        # 构建搜索参数
        search_params = TagSearchParams(
            query=query,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 使用业务处理器处理标签列表逻辑
        handler = TagHandler(db)
        tags_result = await handler.handle_get_all_tags(search_params)

        # 返回标准化响应
        return StandardResponse(
            status="success",
            message=f"成功获取 {len(tags_result['items'])} 个标签",
            data=tags_result
        )

    except Exception as e:
        logger.error(f"获取标签列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取标签列表失败")
```

### 5.2 处理器层实现示例
```python
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.tag_service import TagService
from app.schemas.tag import TagSearchParams
from app.core.log_utils import get_logger

logger = get_logger(__name__)

class TagHandler:
    """标签处理器 - 处理网络请求、日志记录和异常处理"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_service = TagService(db)

    async def handle_get_all_tags(
        self,
        search_params: TagSearchParams
    ) -> Dict[str, Any]:
        """处理获取所有标签请求"""
        try:
            logger.info(
                "处理获取所有标签请求",
                extra={
                    "query": search_params.query,
                    "page": search_params.page,
                    "limit": search_params.limit,
                    "sort_by": search_params.sort_by,
                    "sort_order": search_params.sort_order
                }
            )

            result = await self.tag_service.get_all_tags(search_params)

            logger.info(
                "获取所有标签完成",
                extra={
                    "total": result["total"],
                    "page": result["page"],
                    "limit": result["limit"]
                }
            )

            return result

        except Exception as e:
            logger.error(
                "获取所有标签失败",
                extra={
                    "search_params": search_params.model_dump(),
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取所有标签失败: {str(e)}"
            )
```

### 5.3 服务层实现示例
```python
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.tag import TagRepository
from app.schemas.tag import TagSearchParams

class TagService:
    """标签服务 - 实现核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_repository = TagRepository(db)

    async def get_all_tags(self, search_params: TagSearchParams) -> Dict[str, Any]:
        """获取所有标签"""
        # 调用仓库层获取数据
        tags, total = await self.tag_repository.get_all_tags(
            query=search_params.query,
            skip=(search_params.page - 1) * search_params.limit,
            limit=search_params.limit,
            sort_by=search_params.sort_by,
            sort_order=search_params.sort_order
        )

        # 业务逻辑处理
        return {
            "items": [tag.to_dict() for tag in tags],
            "total": total,
            "page": search_params.page,
            "limit": search_params.limit,
            "has_next": (search_params.page * search_params.limit) < total,
            "has_prev": search_params.page > 1
        }
```

## 6. 数据模型规范

### 6.1 Pydantic 模型定义
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TagBase(BaseModel):
    """标签基础模型"""
    name: str = Field(..., description="标签名称", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="标签描述", max_length=200)

class TagCreate(TagBase):
    """标签创建模型"""
    pass

class TagResponse(TagBase):
    """标签响应模型"""
    id: str = Field(..., description="标签ID")
    usage_count: int = Field(..., description="使用次数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class TagSearchParams(BaseModel):
    """标签搜索参数"""
    query: Optional[str] = Field(None, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页记录数")
    sort_by: str = Field("usage_count", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
```

### 6.2 通用响应模型
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
```

## 7. 错误处理规范

### 7.1 HTTP 状态码使用

| 状态码 | 场景 |
|--------|------|
| 200 OK | 成功请求 |
| 201 Created | 资源创建成功 |
| 204 No Content | 成功无返回内容 |
| 400 Bad Request | 请求参数错误 |
| 401 Unauthorized | 未认证 |
| 403 Forbidden | 权限不足 |
| 404 Not Found | 资源不存在 |
| 422 Unprocessable Entity | 参数验证失败 |
| 500 Internal Server Error | 服务器错误 |

### 7.2 错误码体系
使用统一的错误码分类：
- `AUTH_*` - 认证相关错误
- `VALIDATION_*` - 参数验证错误
- `RESOURCE_*` - 资源相关错误
- `SYSTEM_*` - 系统错误

## 8. 最佳实践

### 8.1 分层架构最佳实践
- **端点层**: 保持简单，只处理 HTTP 相关逻辑
- **处理器层**: 处理网络层异常和日志记录
- **服务层**: 专注于业务逻辑实现
- **仓库层**: 封装数据访问细节

### 8.2 代码组织最佳实践
- 按功能模块组织文件结构
- 保持单一职责原则
- 使用依赖注入管理组件依赖
- 编写清晰的文档字符串

### 8.3 性能优化最佳实践
- 使用异步编程提高并发性能
- 合理使用数据库索引
- 实现适当的缓存策略
- 监控接口响应时间

## 9. 测试规范

### 9.1 单元测试
- 测试服务层业务逻辑
- 使用 Mock 对象隔离外部依赖
- 覆盖主要业务场景

### 9.2 集成测试
- 测试完整的 API 端点
- 验证端到端的业务流程
- 使用测试数据库

## 10. 部署和运维

### 10.1 环境配置
- 开发、测试、生产环境分离
- 环境特定的配置管理
- 密钥和敏感信息安全存储

### 10.2 健康检查
```python
@router.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效