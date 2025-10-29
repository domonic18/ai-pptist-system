# API 响应与日志规范

## 1. 概述

本文档定义了 AI PPTist 项目的统一 API 响应格式和日志记录规范，确保前后端数据交互的一致性和系统的可维护性。

## 2. API 响应规范

### 2.1 设计原则

#### 一致性
- 所有 API 响应遵循相同的结构格式
- 错误处理和成功响应使用统一模式
- 前后端开发人员可以预期相同的响应结构

#### 可读性
- 响应字段命名清晰明确
- 错误信息提供足够上下文
- 支持多语言错误消息

#### 扩展性
- 响应结构支持未来功能扩展
- 兼容现有客户端代码
- 支持版本演进

### 2.2 基础响应格式

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

### 2.3 响应字段说明

| 字段名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| `status` | string | 是 | 响应状态：`success`、`error`、`warning` |
| `message` | string | 是 | 人类可读的响应消息 |
| `data` | any | 否 | 响应数据，成功时包含业务数据 |
| `error_code` | string | 否 | 错误代码，仅在错误时提供 |
| `error_details` | object | 否 | 错误详情，包含调试信息 |
| `timestamp` | string | 是 | ISO 8601 格式的时间戳 |
| `request_id` | string | 是 | 请求唯一标识符，用于追踪 |

### 2.4 成功响应规范

#### 通用成功响应
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

#### 分页响应
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
      "page": 1,
      "limit": 20,
      "has_next": true,
      "has_prev": false
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456"
}
```

#### 空数据响应
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

### 2.5 错误响应规范

#### 通用错误响应
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

#### 标准错误码

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

#### 参数验证错误
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

### 2.6 特定业务响应格式

#### 图片上传响应
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

#### 图片搜索响应
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

### 2.7 HTTP 状态码规范

#### 成功状态码
- `200 OK` - 通用成功响应
- `201 Created` - 资源创建成功
- `202 Accepted` - 请求已接受，处理中
- `204 No Content` - 成功但无内容返回

#### 客户端错误
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 参数验证失败

#### 服务器错误
- `500 Internal Server Error` - 服务器内部错误
- `502 Bad Gateway` - 网关错误
- `503 Service Unavailable` - 服务不可用

### 2.8 流式响应规范

#### 流式响应格式
对于 AI 生成等流式接口，使用 Server-Sent Events (SSE) 格式：

```
event: status
data: {"status": "processing", "progress": 30}

event: chunk
data: {"type": "text", "content": "生成的内容片段"}

event: complete
data: {"status": "completed", "total_tokens": 150}
```

#### 流式事件类型
- `status` - 处理状态更新
- `chunk` - 数据内容块
- `complete` - 处理完成
- `error` - 处理错误

## 3. 日志记录规范

### 3.1 设计原则

#### 一致性
- 所有日志使用统一的格式和结构
- 日志消息模板集中管理
- 支持结构化数据记录

#### 可读性
- 日志消息清晰明确
- 包含足够的上下文信息
- 便于人工阅读和机器解析

#### 可维护性
- 消息模板与代码分离
- 支持参数化消息
- 便于国际化扩展

### 3.2 日志架构

#### 核心组件
1. **LogMessages 类** (`app/core/log_messages.py`)
   - 统一管理所有日志消息模板
   - 支持参数化消息格式
   - 提供结构化数据支持

2. **UnifiedLogger 类** (`app/core/log_utils.py`)
   - 提供标准化的日志记录接口
   - 自动处理异常信息
   - 支持结构化日志数据

#### 使用方式
```python
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

# 获取日志记录器
logger = get_logger(__name__)

# 记录信息级别日志
logger.info(log_messages.START_OPERATION, operation_name="图片上传")

# 记录错误级别日志（带异常）
try:
    # 业务逻辑
    logger.info(log_messages.OPERATION_SUCCESS, operation_name="图片上传")
except Exception as e:
    logger.error(log_messages.OPERATION_FAILED,
                 operation_name="图片上传",
                 exception=e)
```

### 3.3 日志级别规范

#### 日志级别定义

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 调试信息，开发环境使用 | 详细的变量值、中间结果 |
| **INFO** | 业务操作信息 | 操作开始、成功完成、重要状态变更 |
| **WARNING** | 警告信息，不影响主要功能 | 资源不足、配置问题、预期外的状态 |
| **ERROR** | 错误信息，影响单个操作 | 业务逻辑错误、外部服务调用失败 |
| **CRITICAL** | 严重错误，影响系统运行 | 数据库连接失败、关键服务不可用 |

#### 日志内容规范

##### 操作开始日志
```python
logger.info(log_messages.START_OPERATION,
            operation_name="图片列表查询",
            user_id=user_id,
            skip=skip,
            limit=limit)
```

##### 操作成功日志
```python
logger.info(log_messages.OPERATION_SUCCESS,
            operation_name="图片列表查询",
            user_id=user_id,
            result_count=len(images))
```

##### 操作失败日志
```python
try:
    # 业务逻辑
except Exception as e:
    logger.error(log_messages.OPERATION_FAILED,
                 operation_name="图片列表查询",
                 user_id=user_id,
                 error=str(e),
                 error_type=type(e).__name__)
```

### 3.4 消息模板规范

#### 模板命名规范
- 使用英文大写字母和下划线
- 格式：`{模块}_{操作}_{状态}`
- 示例：`IMAGE_LIST_START`, `FILE_UPLOAD_SUCCESS`

#### 参数化消息
消息模板应支持参数化，使用 `{}` 占位符：

```python
# log_messages.py
START_OPERATION = "开始执行操作: {operation_name}"

# 使用
logger.info(log_messages.START_OPERATION, operation_name="图片上传")
```

#### 结构化数据
所有业务相关的上下文信息应作为结构化数据记录：

```python
logger.info(log_messages.IMAGE_LIST_SUCCESS,
            user_id=user_id,
            image_count=len(images),
            total_count=total,
            skip=skip,
            limit=limit)
```

### 3.5 各模块日志规范

#### 图片管理模块

##### 图片列表查询
```python
# 开始查询
logger.info(log_messages.IMAGE_LIST_START,
            user_id=user_id,
            skip=skip,
            limit=limit)

# 查询成功
logger.info(log_messages.IMAGE_LIST_SUCCESS,
            user_id=user_id,
            image_count=len(images),
            total_count=total)

# 查询失败
logger.error(log_messages.IMAGE_LIST_FAILED,
             user_id=user_id,
             error=str(e))
```

##### 图片详情获取
```python
# 开始获取
logger.info(log_messages.IMAGE_DETAIL_START,
            user_id=user_id,
            image_id=image_id)

# 获取成功
logger.info(log_messages.IMAGE_DETAIL_SUCCESS,
            user_id=user_id,
            image_id=image_id)

# 图片不存在
logger.warning(log_messages.IMAGE_NOT_FOUND,
               user_id=user_id,
               image_id=image_id)

# 获取失败
logger.error(log_messages.IMAGE_DETAIL_FAILED,
             user_id=user_id,
             image_id=image_id,
             error=str(e))
```

### 3.6 最佳实践

#### 避免硬编码

❌ **不推荐**（硬编码消息）
```python
logger.info("开始获取图片列表")
```

✅ **推荐**（使用消息模板）
```python
logger.info(log_messages.IMAGE_LIST_START)
```

#### 结构化数据

❌ **不推荐**（信息在消息中）
```python
logger.info(f"用户 {user_id} 获取了 {count} 张图片")
```

✅ **推荐**（结构化数据）
```python
logger.info(log_messages.IMAGE_LIST_SUCCESS,
            user_id=user_id,
            image_count=count)
```

#### 异常处理

❌ **不推荐**（简单的错误记录）
```python
except Exception as e:
    logger.error(f"操作失败: {e}")
```

✅ **推荐**（完整的错误信息）
```python
except Exception as e:
    logger.error(log_messages.OPERATION_FAILED,
                 operation_name="图片上传",
                 error=str(e),
                 error_type=type(e).__name__)
```

## 4. 实施要求

### 4.1 后端实施
1. 所有 API 端点必须使用 `StandardResponse` 模式
2. 错误处理必须使用统一的错误码体系
3. 响应必须包含时间戳和请求 ID
4. 分页接口必须遵循分页规范
5. 所有日志记录必须使用统一的日志系统

### 4.2 前端实施
1. 统一处理响应结构解析
2. 错误处理基于标准错误码
3. 请求追踪使用请求 ID
4. 支持多语言错误消息显示

## 5. 监控和排查

### 5.1 日志查询
使用结构化数据便于日志查询：
```bash
# 查询特定用户的操作
grep "user_id=123" backend.log

# 查询错误日志
grep "ERROR" backend.log

# 查询特定操作
grep "IMAGE_LIST" backend.log
```

### 5.2 性能监控
关键操作应记录耗时信息：
```python
import time

start_time = time.time()
# 执行业务操作
end_time = time.time()

logger.info(log_messages.OPERATION_SUCCESS,
            operation_name="图片处理",
            duration_ms=int((end_time - start_time) * 1000))
```

## 6. 示例代码

### 6.1 Python FastAPI 响应示例
```python
from app.schemas.common import StandardResponse

@router.get("/images/{image_id}")
async def get_image(image_id: str):
    try:
        image = await image_service.get_image(image_id)
        return StandardResponse(
            status="success",
            message="图片获取成功",
            data=image.dict(),
            request_id=request.state.request_id
        )
    except ImageNotFoundError:
        return StandardResponse(
            status="error",
            message="图片不存在",
            error_code="IMAGE_NOT_FOUND",
            request_id=request.state.request_id
        )
```

### 6.2 完整的业务操作示例
```python
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

logger = get_logger(__name__)

async def get_image_list(user_id: str, skip: int, limit: int):
    """获取图片列表"""
    try:
        # 记录操作开始
        logger.info(log_messages.IMAGE_LIST_START,
                    user_id=user_id, skip=skip, limit=limit)

        # 执行业务逻辑
        result = await image_service.list_images(user_id, skip, limit)

        # 记录操作成功
        logger.info(log_messages.IMAGE_LIST_SUCCESS,
                    user_id=user_id,
                    image_count=len(result["items"]),
                    total_count=result["total"])

        return result

    except Exception as e:
        # 记录操作失败
        logger.error(log_messages.IMAGE_LIST_FAILED,
                     user_id=user_id,
                     error=str(e),
                     error_type=type(e).__name__)
        raise
```

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效