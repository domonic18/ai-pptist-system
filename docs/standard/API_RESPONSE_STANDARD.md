# API 响应规范标准

## 1. 概述

本文档定义了 AI 幻灯片助手项目的统一 API 响应格式规范，旨在确保前后端数据交互的一致性和可维护性。所有 API 响应必须遵循此规范。

## 2. 设计原则

### 2.1 一致性
- 所有 API 响应遵循相同的结构格式
- 错误处理和成功响应使用统一模式
- 前后端开发人员可以预期相同的响应结构

### 2.2 可读性
- 响应字段命名清晰明确
- 错误信息提供足够上下文
- 支持多语言错误消息

### 2.3 扩展性
- 响应结构支持未来功能扩展
- 兼容现有客户端代码
- 支持版本演进

## 3. 基础响应格式

### 3.1 标准响应结构
所有 API 响应必须使用以下基础结构：

```json
{
  "status": "success",
  "message": "操作成功",
  "data": {},
  "error_code": null,
  "error_details": null,
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 3.2 响应字段说明

| 字段名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `status` | string | 是 | 响应状态：`success`、`error`、`warning` |
| `message` | string | 是 | 人类可读的响应消息 |
| `data` | any | 否 | 响应数据，成功时包含业务数据 |
| `error_code` | string | 否 | 错误代码，仅在错误时提供 |
| `error_details` | object | 否 | 错误详情，包含调试信息 |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |
| `request_id` | string | 是 | 请求唯一标识符，用于追踪 |

## 4. 成功响应规范

### 4.1 通用成功响应
```json
{
  "status": "success",
  "message": "操作成功",
  "data": {
    // 业务特定数据
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 4.2 分页响应
对于列表查询接口，必须使用标准分页格式：

```json
{
  "status": "success",
  "message": "获取成功",
  "data": {
    "items": [
      // 数据项列表
    ],
    "pagination": {
      "total": 100,
      "skip": 0,
      "limit": 20,
      "has_next": true,
      "has_prev": false
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 4.3 空数据响应
当没有数据返回时：
```json
{
  "status": "success",
  "message": "查询成功，无数据",
  "data": null,
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

## 5. 错误响应规范

### 5.1 通用错误响应
```json
{
  "status": "error",
  "message": "错误描述信息",
  "data": null,
  "error_code": "ERROR_CODE",
  "error_details": {
    "field": "具体字段",
    "reason": "详细原因",
    "suggestion": "解决建议"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 5.2 标准错误码

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `INVALID_REQUEST` | 400 | 无效请求参数 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `UNAUTHORIZED` | 401 | 未认证 |
| `TOKEN_EXPIRED` | 401 | Token 过期 |
| `INVALID_TOKEN` | 401 | 无效 Token |
| `IMAGE_NOT_FOUND` | 404 | 图片不存在 |
| `IMAGE_UPLOAD_FAILED` | 500 | 图片上传失败 |
| `IMAGE_TOO_LARGE` | 400 | 图片过大 |
| `INVALID_IMAGE_FORMAT` | 400 | 无效图片格式 |
| `STORAGE_ERROR` | 500 | 存储错误 |
| `SEARCH_FAILED` | 500 | 搜索失败 |
| `GENERATION_ERROR` | 500 | 生成失败 |

### 5.3 参数验证错误
```json
{
  "status": "error",
  "message": "请求参数校验失败",
  "data": null,
  "error_code": "INVALID_REQUEST",
  "error_details": {
    "validation_errors": [
      {
        "field": "email",
        "message": "邮箱格式不正确",
        "value": "invalid-email"
      },
      {
        "field": "password",
        "message": "密码长度至少8位",
        "value": "short"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

## 6. 特定业务响应格式

### 6.1 图片上传响应
```json
{
  "status": "success",
  "message": "图片上传成功",
  "data": {
    "image_id": "img_123456",
    "image_url": "https://example.com/images/img_123456.jpg",
    "cos_key": "users/123/images/img_123456.jpg",
    "filename": "example.jpg",
    "file_size": 1024000,
    "mime_type": "image/jpeg"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 6.2 图片搜索响应
```json
{
  "status": "success",
  "message": "搜索完成",
  "data": {
    "results": [
      {
        "id": "img_123456",
        "prompt": "生成提示词",
        "model_name": "dall-e-3",
        "url": "https://example.com/images/img_123456.jpg",
        "width": 1024,
        "height": 768,
        "file_size": 512000,
        "match_type": "semantic",
        "confidence": 0.92
      }
    ],
    "total": 15,
    "has_more": true
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

### 6.3 预签名 URL 响应
```json
{
  "status": "success",
  "message": "预签名URL生成成功",
  "data": {
    "upload_url": "https://cos.example.com/presigned-url",
    "download_url": "https://example.com/files/filename.jpg",
    "cos_key": "users/123/files/filename.jpg",
    "expires_at": "2024-01-01T12:05:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

## 7. HTTP 状态码规范

### 7.1 成功状态码
- `200 OK` - 通用成功响应
- `201 Created` - 资源创建成功
- `202 Accepted` - 请求已接受，处理中
- `204 No Content` - 成功但无内容返回

### 7.2 客户端错误
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 参数验证失败

### 7.3 服务器错误
- `500 Internal Server Error` - 服务器内部错误
- `502 Bad Gateway` - 网关错误
- `503 Service Unavailable` - 服务不可用

## 8. 响应头规范

### 8.1 标准响应头
```http
Content-Type: application/json; charset=utf-8
X-Request-ID: req_123456
X-API-Version: v1
Deprecation: false
RateLimit-Limit: 100
RateLimit-Remaining: 99
RateLimit-Reset: 60
```

### 8.2 分页头信息（可选）
对于分页接口，可以包含以下头信息：
```http
X-Total-Count: 100
X-Page-Count: 5
X-Current-Page: 1
X-Per-Page: 20
```

## 9. 流式响应规范

### 9.1 流式响应格式
对于 AI 生成等流式接口，使用 Server-Sent Events (SSE) 格式：

```
event: status
data: {"status": "processing", "progress": 30}


event: chunk
data: {"type": "text", "content": "生成的内容片段"}


event: complete
data: {"status": "completed", "total_tokens": 150}
```

### 9.2 流式事件类型
- `status` - 处理状态更新
- `chunk` - 数据内容块
- `complete` - 处理完成
- `error` - 处理错误

## 10. 版本管理

### 10.1 API 版本控制
- 所有 API 必须包含版本前缀：`/api/v1/`
- 响应头包含 API 版本信息：`X-API-Version: v1`
- 弃用接口在响应头中标记：`Deprecation: true; sunset="2024-12-31"`

### 10.2 向后兼容
- 新增字段必须为可选
- 不能删除或重命名字段
- 字段语义不能改变

## 11. 实施要求

### 11.1 后端实施
1. 所有 API 端点必须使用 `StandardResponse` 模式
2. 错误处理必须使用统一的错误码体系
3. 响应必须包含时间戳和请求 ID
4. 分页接口必须遵循分页规范

### 11.2 前端实施
1. 统一处理响应结构解析
2. 错误处理基于标准错误码
3. 请求追踪使用请求 ID
4. 支持多语言错误消息显示

## 12. 示例代码

### 12.1 Python FastAPI 示例
```python
from app.schemas.common import SuccessResponse, ErrorResponse

@router.get("/images/{image_id}")
async def get_image(image_id: str):
    try:
        image = await image_service.get_image(image_id)
        return SuccessResponse(
            message="图片获取成功",
            data=image.dict(),
            request_id=request.state.request_id
        )
    except ImageNotFoundError:
        return ErrorResponse(
            message="图片不存在",
            error_code=ErrorCode.IMAGE_NOT_FOUND,
            request_id=request.state.request_id
        )
```

### 12.2 TypeScript 前端示例
```typescript
interface StandardResponse<T = any> {
  status: 'success' | 'error' | 'warning';
  message: string;
  data?: T;
  error_code?: string;
  error_details?: any;
  timestamp: string;
  request_id: string;
}

// 统一响应处理
async function handleResponse<T>(response: Response): Promise<T> {
  const data: StandardResponse<T> = await response.json();

  if (data.status === 'success') {
    return data.data!;
  } else {
    throw new ApiError(data.message, data.error_code, data.error_details);
  }
}
```

## 13. 监控和日志

### 13.1 日志记录
- 记录所有请求和响应
- 包含请求 ID 用于追踪
- 记录响应状态和错误信息

### 13.2 监控指标
- 响应时间分布
- 错误率统计
- 各端点调用频率
- 分页查询性能

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效