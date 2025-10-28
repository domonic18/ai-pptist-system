# 日志记录规范标准

## 1. 概述

本文档定义了 AI 幻灯片助手项目的统一日志记录规范，旨在实现结构化、可维护和可监控的日志系统。

## 2. 设计原则

### 2.1 一致性
- 所有日志使用统一的格式和结构
- 日志消息模板集中管理
- 支持结构化数据记录

### 2.2 可读性
- 日志消息清晰明确
- 包含足够的上下文信息
- 便于人工阅读和机器解析

### 2.3 可维护性
- 消息模板与代码分离
- 支持参数化消息
- 便于国际化扩展

## 3. 日志架构

### 3.1 核心组件

1. **LogMessages 类** (`app/core/log_messages.py`)
   - 统一管理所有日志消息模板
   - 支持参数化消息格式
   - 提供结构化数据支持

2. **UnifiedLogger 类** (`app/core/log_utils.py`)
   - 提供标准化的日志记录接口
   - 自动处理异常信息
   - 支持结构化日志数据

### 3.2 使用方式

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

## 4. 日志级别规范

### 4.1 日志级别定义

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 调试信息，开发环境使用 | 详细的变量值、中间结果 |
| **INFO** | 业务操作信息 | 操作开始、成功完成、重要状态变更 |
| **WARNING** | 警告信息，不影响主要功能 | 资源不足、配置问题、预期外的状态 |
| **ERROR** | 错误信息，影响单个操作 | 业务逻辑错误、外部服务调用失败 |
| **CRITICAL** | 严重错误，影响系统运行 | 数据库连接失败、关键服务不可用 |

### 4.2 日志内容规范

#### 操作开始日志
```python
logger.info(log_messages.START_OPERATION,
            operation_name="图片列表查询",
            user_id=user_id,
            skip=skip,
            limit=limit)
```

#### 操作成功日志
```python
logger.info(log_messages.OPERATION_SUCCESS,
            operation_name="图片列表查询",
            user_id=user_id,
            result_count=len(images))
```

#### 操作失败日志
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

## 5. 消息模板规范

### 5.1 模板命名规范

- 使用英文大写字母和下划线
- 格式：`{模块}_{操作}_{状态}`
- 示例：`IMAGE_LIST_START`, `FILE_UPLOAD_SUCCESS`

### 5.2 参数化消息

消息模板应支持参数化，使用 `{}` 占位符：

```python
# log_messages.py
START_OPERATION = "开始执行操作: {operation_name}"

# 使用
logger.info(log_messages.START_OPERATION, operation_name="图片上传")
```

### 5.3 结构化数据

所有业务相关的上下文信息应作为结构化数据记录：

```python
logger.info(log_messages.IMAGE_LIST_SUCCESS,
            user_id=user_id,
            image_count=len(images),
            total_count=total,
            skip=skip,
            limit=limit)
```

## 6. 各模块日志规范

### 6.1 图片管理模块

#### 图片列表查询
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

#### 图片详情获取
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

### 6.2 文件上传模块

#### 文件上传
```python
# 开始上传
logger.info(log_messages.FILE_UPLOAD_START,
            user_id=user_id,
            filename=filename,
            file_size=file_size)

# 上传成功
logger.info(log_messages.FILE_UPLOAD_SUCCESS,
            user_id=user_id,
            filename=filename,
            file_size=file_size)

# 上传失败
logger.error(log_messages.FILE_UPLOAD_FAILED,
             user_id=user_id,
             filename=filename,
             error=str(e))

# 文件验证失败
logger.warning(log_messages.FILE_VALIDATION_FAILED,
               user_id=user_id,
               filename=filename,
               reason=validation_error)
```

### 6.3 数据库操作模块

#### 数据库查询
```python
# 开始查询
logger.info(log_messages.DB_QUERY_START,
            operation_name="用户信息查询",
            query_params=params)

# 查询成功
logger.info(log_messages.DB_QUERY_SUCCESS,
            operation_name="用户信息查询",
            result_count=len(results))

# 查询失败
logger.error(log_messages.DB_QUERY_FAILED,
             operation_name="用户信息查询",
             error=str(e))
```

## 7. 最佳实践

### 7.1 避免硬编码

❌ **不推荐**（硬编码消息）
```python
logger.info("开始获取图片列表")
```

✅ **推荐**（使用消息模板）
```python
logger.info(log_messages.IMAGE_LIST_START)
```

### 7.2 结构化数据

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

### 7.3 异常处理

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

## 8. 配置和管理

### 8.1 日志配置

日志系统配置位于 `app/core/log_utils.py` 的 `setup_logging()` 函数：

```python
# 配置日志系统
setup_logging()

# 获取日志记录器
logger = get_logger(__name__)
```

### 8.2 环境配置

- **开发环境**: 输出 DEBUG 级别日志到控制台
- **生产环境**: 输出 INFO 级别日志到文件
- **日志轮转**: 支持按大小或时间轮转

### 8.3 性能考虑

- 避免在热路径中执行昂贵的日志操作
- 使用适当的日志级别减少生产环境日志量
- 结构化数据便于后续处理和分析

## 9. 监控和排查

### 9.1 日志查询

使用结构化数据便于日志查询：
```bash
# 查询特定用户的操作
grep "user_id=123" backend.log

# 查询错误日志
grep "ERROR" backend.log

# 查询特定操作
grep "IMAGE_LIST" backend.log
```

### 9.2 性能监控

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

## 10. 维护指南

### 10.1 添加新消息模板

1. 在 `app/core/log_messages.py` 中添加新的消息常量
2. 使用清晰的命名和描述
3. 支持必要的参数化

### 10.2 修改现有消息

1. 直接修改 `log_messages.py` 中的消息模板
2. 确保不破坏现有的参数结构
3. 更新相关文档

### 10.3 国际化支持

消息模板设计支持未来的国际化：
- 所有消息使用英文定义
- 参数化设计便于翻译
- 集中管理便于维护

## 11. 示例代码

### 11.1 完整的业务操作示例

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

### 11.2 API 端点日志示例

```python
from fastapi import APIRouter, Depends
from app.core.log_utils import get_logger
from app.core.log_messages import log_messages

router = APIRouter()
logger = get_logger(__name__)

@router.get("/images")
async def list_images(
    user_id: str,
    skip: int = 0,
    limit: int = 20
):
    """获取图片列表API端点"""
    try:
        logger.info(log_messages.IMAGE_LIST_START,
                    user_id=user_id, skip=skip, limit=limit)

        # 业务逻辑
        images = await image_service.get_images(user_id, skip, limit)

        logger.info(log_messages.IMAGE_LIST_SUCCESS,
                    user_id=user_id,
                    image_count=len(images))

        return {"images": images}

    except Exception as e:
        logger.error(log_messages.IMAGE_LIST_FAILED,
                     user_id=user_id,
                     error=str(e))
        raise
```

## 12. 与其他规范的集成

### 12.1 与 API 响应规范集成

日志记录应与 API 响应规范保持一致：
```python
# 记录API请求信息
logger.info(log_messages.API_REQUEST_START,
            method=request.method,
            path=request.url.path,
            user_id=current_user.id,
            request_id=request.state.request_id)
```

### 12.2 与错误处理规范集成

错误日志应包含标准错误码：
```python
try:
    # 业务逻辑
except Exception as e:
    logger.error(log_messages.OPERATION_FAILED,
                 operation_name="图片上传",
                 error_code="IMAGE_UPLOAD_FAILED",
                 error=str(e))
    raise
```

---

**最后更新**: 2024年12月
**版本**: v1.0.0
**生效日期**: 立即生效