# API 设计指南

## 1. 概述

本文档提供 AI 幻灯片助手项目的 API 设计原则和最佳实践，确保 API 的一致性、可用性和可维护性。

## 2. 设计原则

### 2.1 RESTful 原则
- **资源导向**: 使用名词表示资源，动词表示操作
- **无状态**: 每个请求包含所有必要信息
- **统一接口**: 使用标准 HTTP 方法和状态码
- **可缓存**: 支持适当的缓存策略

### 2.2 一致性原则
- 命名约定统一
- 响应格式标准化
- 错误处理一致
- 版本管理规范

### 2.3 用户体验原则
- 接口直观易用
- 文档清晰完整
- 错误信息有帮助
- 向后兼容

## 3. 资源设计

### 3.1 资源命名
- 使用复数名词: `/images` 而不是 `/image`
- 使用连字符: `/search-results` 而不是 `/searchResults`
- 全部小写: `/user-preferences` 而不是 `/UserPreferences`

### 3.2 资源层次
```
# 正确示例
/users/{user_id}/images
/users/{user_id}/images/{image_id}
/presentations/{presentation_id}/slides

# 错误示例
/getUserImages?user_id=123  # 应该使用路径参数
```

### 3.3 常用资源端点

| 资源 | 端点 | 方法 | 描述 |
|------|------|------|------|
| 用户 | `/users` | GET | 获取用户列表 |
| 用户 | `/users/{id}` | GET | 获取用户详情 |
| 图片 | `/images` | GET | 获取图片列表 |
| 图片 | `/images` | POST | 创建图片 |
| 图片 | `/images/{id}` | GET | 获取图片详情 |
| 图片 | `/images/{id}` | DELETE | 删除图片 |
| 演示稿 | `/presentations` | GET | 获取演示稿列表 |
| 演示稿 | `/presentations` | POST | 创建演示稿 |

## 4. 端点设计

### 4.1 HTTP 方法使用

| 方法 | 用途 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 获取资源 | 是 | 是 |
| POST | 创建资源 | 否 | 否 |
| PUT | 替换资源 | 是 | 否 |
| PATCH | 部分更新 | 否 | 否 |
| DELETE | 删除资源 | 是 | 否 |

### 4.2 集合操作端点

```
# 批量操作
POST /images/batch/delete    # 批量删除图片
POST /images/batch/update    # 批量更新图片

# 特定操作
POST /images/{id}/favorite   # 收藏图片
DELETE /images/{id}/favorite # 取消收藏
```

### 4.3 搜索和过滤端点

```
# 搜索接口
POST /images/search          # 搜索图片（复杂查询）
GET /images?search=keyword   # 简单搜索（查询参数）

# 过滤接口
GET /images?type=jpeg&size=large          # 多条件过滤
GET /images?created_after=2024-01-01      # 时间范围过滤
GET /images?tags=ai,technology            # 标签过滤
```

## 5. 参数设计

### 5.1 路径参数
```python
# 正确
@router.get("/images/{image_id}")
async def get_image(image_id: str):
    pass

# 错误 - 使用查询参数表示资源标识
@router.get("/images")
async def get_image(image_id: str):  # 应该使用路径参数
    pass
```

### 5.2 查询参数

| 参数类型 | 示例 | 描述 |
|----------|------|------|
| 分页 | `?page=1&limit=20` | 分页控制 |
| 排序 | `?sort=created_at&order=desc` | 排序方式 |
| 过滤 | `?status=active&type=image` | 条件过滤 |
| 搜索 | `?q=keyword` | 搜索关键词 |
| 字段选择 | `?fields=id,name,url` | 选择返回字段 |

### 5.3 请求体参数
- 使用 JSON 格式
- 复杂对象使用嵌套结构
- 文件上传使用 `multipart/form-data`

## 6. 响应设计

### 6.1 成功响应
```json
{
  "status": "success",
  "message": "操作成功",
  "data": {
    // 业务数据
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 6.2 错误响应
```json
{
  "status": "error",
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "error_details": {
    "field": "email",
    "reason": "格式不正确"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 6.3 分页响应
```json
{
  "data": {
    "items": [],
    "pagination": {
      "total": 100,
      "page": 1,
      "limit": 20,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

## 7. 错误处理

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

## 8. 版本管理

### 8.1 版本策略
- URL 路径版本控制: `/api/v1/images`
- 支持最多 3 个活跃版本
- 弃用版本提供迁移期

### 8.2 版本演进规则
1. 新增字段必须为可选
2. 不能删除已有字段
3. 字段语义不能改变
4. 新增端点不影响现有功能

## 9. 安全设计

### 9.1 认证授权
- 使用 JWT Token 认证
- 基于角色的访问控制 (RBAC)
- 资源级别的权限验证

### 9.2 输入验证
- 所有输入必须验证
- 使用 Pydantic 模型验证
- 防范 SQL 注入和 XSS 攻击

### 9.3 速率限制
- 基于用户 ID 的速率限制
- 敏感操作额外限制
- 清晰的速率限制头信息

## 10. 性能优化

### 10.1 缓存策略
- 适当使用 HTTP 缓存头
- 数据库查询缓存
- CDN 静态资源缓存

### 10.2 分页优化
- 默认分页大小限制
- 游标分页支持
- 总数统计可选

### 10.3 字段选择
```
# 支持字段选择，减少数据传输
GET /users?fields=id,name,avatar
```

## 11. 文档规范

### 11.1 OpenAPI 规范
- 所有 API 必须有 OpenAPI 文档
- 使用代码注释生成文档
- 保持文档与代码同步

### 11.2 端点文档要求
每个端点必须包含：
- 简要描述
- 参数说明
- 响应示例
- 错误情况
- 权限要求

## 12. 测试要求

### 12.1 测试覆盖
- 单元测试覆盖业务逻辑
- 集成测试覆盖 API 端点
- 性能测试评估接口性能

### 12.2 测试数据
- 使用测试专用数据
- 测试后清理数据
- 支持并行测试执行

## 13. 监控和日志

### 13.1 日志记录
- 记录请求和响应摘要
- 包含请求 ID 用于追踪
- 记录性能指标

### 13.2 监控指标
- 接口响应时间
- 错误率和错误类型
- 调用频率和流量

## 14. 部署和运维

### 14.1 环境配置
- 开发、测试、生产环境分离
- 环境特定的配置管理
- 密钥和敏感信息安全存储

### 14.2 健康检查
```
GET /health          # 应用健康状态
GET /health/db       # 数据库健康状态
GET /health/redis    # Redis 健康状态
```

## 15. 示例代码

### 15.1 完整端点示例
```python
@router.get(
    "/images",
    response_model=StandardResponse,
    summary="获取图片列表",
    description="分页获取用户图片列表，支持搜索和过滤"
)
async def list_images(
    pagination: PaginationRequest = Depends(),
    search: Optional[str] = None,
    image_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取图片列表

    Args:
        pagination: 分页参数
        search: 搜索关键词
        image_type: 图片类型过滤
        current_user: 当前用户
        db: 数据库会话

    Returns:
        StandardResponse: 包含图片列表的响应
    """
    try:
        # 业务逻辑处理
        images, total = await image_service.list_images(
            user_id=str(current_user.id),
            skip=pagination.skip,
            limit=pagination.limit,
            search=search,
            image_type=image_type
        )

        # 构建分页响应
        pagination_data = PaginationResponse(
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
            has_next=pagination.skip + pagination.limit < total,
            has_prev=pagination.skip > 0
        )

        return SuccessResponse(
            message="图片列表获取成功",
            data={
                "items": images,
                "pagination": pagination_data
            },
            request_id=request.state.request_id
        )

    except Exception as e:
        logger.error(f"获取图片列表失败: {e}")
        return ErrorResponse(
            message="获取图片列表失败",
            error_code=ErrorCode.INTERNAL_ERROR,
            request_id=request.state.request_id
        )
```

## 16. 工具和库

### 16.1 推荐工具
- **FastAPI**: Web 框架
- **Pydantic**: 数据验证
- **SQLAlchemy**: ORM
- **pytest**: 测试框架
- **OpenAPI**: API 文档

### 16.2 开发约定
- 使用类型注解
- 遵循 PEP 8 代码风格
- 编写单元测试
- 代码审查要求

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效