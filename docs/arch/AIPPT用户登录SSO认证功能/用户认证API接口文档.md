# 用户认证API接口文档

## 文档信息

| 项目     | 内容                           |
| -------- | ------------------------------ |
| 文档名称 | AI-PPTist 用户认证API接口文档  |
| 文档版本 | v1.0.0                         |
| 创建日期 | 2026-01-12                     |
| 项目名称 | AI-PPTist                      |
| 文档状态 | 完成                           |
| API版本 | v1                              |

---

## 目录

1. [接口概述](#1-接口概述)
2. [通用说明](#2-通用说明)
3. [认证接口](#3-认证接口)
4. [会话管理接口](#4-会话管理接口)
5. [用户信息接口](#5-用户信息接口)
6. [错误码说明](#6-错误码说明)
7. [附录](#7-附录)

---

## 1. 接口概述

### 1.1 基础信息

- **Base URL**: `http://localhost:8080/api/v1/auth`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 1.2 接口列表

| 序号 | 接口名称        | 方法   | 路径                     | 认证要求 |
|------| --------------- | ------ | ------------------------ | -------- |
| 1    | 用户注册        | POST   | `/register`              | 否       |
| 2    | 用户登录        | POST   | `/login`                 | 否       |
| 3    | 刷新访问令牌    | POST   | `/refresh`               | 否       |
| 4    | 用户登出        | POST   | `/logout`                | 是       |
| 5    | 获取当前用户    | GET    | `/me`                    | 是       |
| 6    | 获取会话列表    | GET    | `/sessions`              | 是       |
| 7    | 撤销指定会话    | POST   | `/sessions/{id}/revoke`  | 是       |
| 8    | 登出所有设备    | POST   | `/logout-all`            | 是       |

---

## 2. 通用说明

### 2.1 请求头

#### 2.1.1 公共请求头

所有请求必须包含以下请求头：

```http
Content-Type: application/json
Accept: application/json
```

#### 2.1.2 认证请求头

需要认证的接口必须包含以下请求头：

```http
Authorization: Bearer <access_token>
```

### 2.2 响应格式

所有接口响应遵循统一格式：

```typescript
interface StandardResponse<T> {
  status: 'success' | 'error'     // 响应状态
  message: string                    // 响应消息
  data?: T                          // 响应数据
  error?: {                         // 错误信息（仅status为error时）
    code: string                    // 错误码
    message: string                 // 错误消息
    details?: any                   // 错误详情
  }
  timestamp: string                  // 响应时间戳（ISO 8601格式）
  request_id: string                // 请求ID（用于日志追踪）
}
```

### 2.3 时间格式

所有时间字段使用 ISO 8601 格式（UTC时区）：

```json
"created_at": "2026-01-12T10:30:00Z"
"expires_at": "2026-01-12T11:30:00Z"
```

### 2.4 分页参数

列表接口支持分页查询：

| 参数 | 类型     | 默认值 | 说明               |
| ---- | -------- | ------ | ------------------ |
| skip | integer  | 0      | 跳过的记录数       |
| limit | integer  | 20     | 返回的记录数限制 |

---

## 3. 认证接口

### 3.1 用户注册

#### 3.1.1 接口信息

- **接口名称**: 用户注册
- **接口路径**: `POST /api/v1/auth/register`
- **认证要求**: 否
- **功能描述**: 创建新用户账户，注册成功后自动登录

#### 3.1.2 请求参数

**请求体 (Body)**:

```json
{
  "email": "user@example.com",
  "name": "张三",
  "password": "Password123",
  "confirm_password": "Password123"
}
```

| 字段             | 类型     | 必填 | 说明                         |
| ---------------- | -------- | ---- | ---------------------------- |
| email            | string   | 是   | 用户邮箱（邮箱格式）       |
| name             | string   | 是   | 用户姓名（2-100个字符）    |
| password         | string   | 是   | 用户密码（至少8位）         |
| confirm_password | string   | 是   | 确认密码（必须与密码一致）   |

#### 3.1.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "注册成功",
  "data": {
    "user": {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "email": "user@example.com",
      "name": "张三",
      "role": "USER",
      "is_active": true,
      "is_superuser": false,
      "auth_type": "password",
      "avatar_url": null,
      "bio": null,
      "created_at": "2026-01-12T10:30:00Z",
      "last_login_at": "2026-01-12T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_at": "2026-01-12T11:30:00Z",
    "refresh_expires_at": "2026-02-11T10:30:00Z"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**错误响应** (400 Bad Request):

```json
{
  "status": "error",
  "message": "请求参数验证失败",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "该邮箱已被注册",
    "details": {
      "field": "email",
      "constraint": "unique"
    }
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

#### 3.1.4 验证规则

| 字段             | 验证规则                           |
| ---------------- | ---------------------------------- |
| email            | 邮箱格式验证，必须唯一               |
| name             | 长度2-100字符                       |
| password         | 至少8个字符，建议包含大小写字母和数字 |
| confirm_password | 必须与password字段完全一致           |

---

### 3.2 用户登录

#### 3.2.1 接口信息

- **接口名称**: 用户登录
- **接口路径**: `POST /api/v1/auth/login`
- **认证要求**: 否
- **功能描述**: 使用邮箱和密码进行用户登录，成功后返回访问令牌

#### 3.2.2 请求参数

**请求体 (Body)**:

```json
{
  "email": "user@example.com",
  "password": "Password123"
}
```

| 字段     | 类型   | 必填 | 说明                   |
| -------- | ------ | ---- | ---------------------- |
| email    | string | 是   | 用户邮箱（邮箱格式） |
| password | string | 是   | 用户密码               |

#### 3.2.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_at": "2026-01-12T11:30:00Z",
    "refresh_expires_at": "2026-02-11T10:30:00Z",
    "user": {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "email": "user@example.com",
      "name": "张三",
      "role": "USER",
      "is_active": true,
      "is_superuser": false,
      "auth_type": "password",
      "avatar_url": null,
      "bio": null,
      "created_at": "2026-01-12T10:30:00Z",
      "last_login_at": "2026-01-12T10:30:00Z"
    }
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**错误响应** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "认证失败",
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "邮箱或密码错误"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**账户被禁用** (403 Forbidden):

```json
{
  "status": "error",
  "message": "账户已被禁用，请联系管理员",
  "error": {
    "code": "ACCOUNT_DISABLED",
    "message": "账户已被禁用，请联系管理员"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

### 3.3 刷新访问令牌

#### 3.3.1 接口信息

- **接口名称**: 刷新访问令牌
- **接口路径**: `POST /api/v1/auth/refresh`
- **认证要求**: 否（使用 refresh_token 进行认证）
- **功能描述**: 使用刷新令牌获取新的访问令牌和刷新令牌

**重要说明**: 每次刷新 token 时，`refresh_token` 也会更新。客户端必须保存新的 `refresh_token` 用于下次刷新。

#### 3.3.2 请求参数

**请求体 (Body)**:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

| 字段          | 类型   | 必填 | 说明             |
| ------------- | ------ | ---- | ---------------- |
| refresh_token | string | 是   | 刷新令牌         |

#### 3.3.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "Token刷新成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_at": "2026-01-12T11:30:00Z",
    "refresh_expires_at": "2026-02-11T10:30:00Z"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**Refresh Token 无效或过期** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "令牌无效或已过期",
  "error": {
    "code": "INVALID_REFRESH_TOKEN",
    "message": "刷新令牌无效或已过期，请重新登录"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**会话已撤销** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "会话已撤销",
  "error": {
    "code": "SESSION_REVOKED",
    "message": "该会话已被撤销，请重新登录"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

#### 3.3.4 客户端处理建议

1. **刷新时机**：
   - API返回401错误时
   - Access Token即将过期前（提前5分钟）

2. **刷新成功后**：
   - 更新本地存储的 access_token
   - **必须**更新本地存储的 refresh_token（每次刷新都会返回新的）
   - 重试原请求

3. **刷新失败后**：
   - 清除本地存储的所有 token
   - 跳转到登录页

---

### 3.4 用户登出

#### 3.4.1 接口信息

- **接口名称**: 用户登出
- **接口路径**: `POST /api/v1/auth/logout`
- **认证要求**: 是
- **功能描述**: 登出当前用户并撤销当前会话

#### 3.4.2 请求参数

**请求头**:

```http
Authorization: Bearer <access_token>
```

**请求体**: 无

#### 3.4.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "登出成功",
  "data": {
    "message": "登出成功"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**未认证** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "未认证",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "请先登录"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

## 4. 会话管理接口

### 4.1 获取会话列表

#### 4.1.1 接口信息

- **接口名称**: 获取用户所有会话
- **接口路径**: `GET /api/v1/auth/sessions`
- **认证要求**: 是
- **功能描述**: 获取当前用户的所有活跃登录会话

#### 4.1.2 请求参数

**请求头**:

```http
Authorization: Bearer <access_token>
```

**查询参数**:

| 参数 | 类型    | 必填 | 默认值 | 说明               |
| ---- | ------- | ---- | ------ | ------------------ |
| skip | integer | 否   | 0      | 跳过的记录数       |
| limit | integer | 否   | 20     | 返回的记录数限制   |

#### 4.1.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "获取会话列表成功",
  "data": {
    "sessions": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "created_at": "2026-01-12T10:00:00Z",
        "expires_at": "2026-01-12T11:00:00Z",
        "is_current": true
      },
      {
        "id": "a1b2c3d4e-5f6g-7h8i-9j0k-1l2m3n4o5p6q7",
        "ip_address": "192.168.1.101",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
        "created_at": "2026-01-12T09:00:00Z",
        "expires_at": "2026-01-12T10:00:00Z",
        "is_current": false
      }
    ],
    "total": 2
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

### 4.2 撤销指定会话

#### 4.2.1 接口信息

- **接口名称**: 撤销指定会话
- **接口路径**: `POST /api/v1/auth/sessions/{session_id}/revoke`
- **认证要求**: 是
- **功能描述**: 撤销用户在指定设备上的登录会话

#### 4.2.2 请求参数

**路径参数**:

| 参数       | 类型   | 必填 | 说明       |
| ---------- | ------ | ---- | ---------- |
| session_id | string | 是   | 会话ID     |

**请求头**:

```http
Authorization: Bearer <access_token>
```

#### 4.2.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "会话已撤销",
  "data": {
    "session_id": "a1b2c3d4e-5f6g-7h8i-9j0k-1l2m3n4o5p6q7"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**会话不存在** (404 Not Found):

```json
{
  "status": "error",
  "message": "会话不存在",
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "指定的会话不存在或已被撤销"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

### 4.3 登出所有设备

#### 4.3.1 接口信息

- **接口名称**: 登出所有设备
- **接口路径**: `POST /api/v1/auth/logout-all`
- **认证要求**: 是
- **功能描述**: 撤销用户在所有设备上的登录会话

#### 4.3.2 请求参数

**请求头**:

```http
Authorization: Bearer <access_token>
```

**请求体**: 无

#### 4.3.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "已撤销 2 个设备的登录会话",
  "data": {
    "revoked_count": 2
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

## 5. 用户信息接口

### 5.1 获取当前用户信息

#### 5.1.1 接口信息

- **接口名称**: 获取当前用户信息
- **接口路径**: `GET /api/v1/auth/me`
- **认证要求**: 是
- **功能描述**: 获取当前登录用户的详细信息

#### 5.1.2 请求参数

**请求头**:

```http
Authorization: Bearer <access_token>
```

#### 5.1.3 响应示例

**成功响应** (200 OK):

```json
{
  "status": "success",
  "message": "获取用户信息成功",
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "email": "user@example.com",
    "name": "张三",
    "role": "USER",
    "is_active": true,
    "is_superuser": false,
    "auth_type": "password",
    "avatar_url": null,
    "bio": null,
    "created_at": "2026-01-12T10:00:00Z",
    "last_login_at": "2026-01-12T10:30:00Z"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

**未认证** (401 Unauthorized):

```json
{
  "status": "error",
  "message": "未认证",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "请先登录"
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

## 6. 错误码说明

### 6.1 通用错误码

| 错误码                  | HTTP状态码 | 说明                           |
| ----------------------- | ---------- | ------------------------------ |
| VALIDATION_ERROR       | 400       | 请求参数验证失败               |
| UNAUTHORIZED           | 401       | 未认证或令牌无效               |
| ACCOUNT_DISABLED       | 403       | 账户已被禁用                   |
| NOT_FOUND              | 404       | 资源不存在                     |
| INTERNAL_SERVER_ERROR  | 500       | 服务器内部错误                 |

### 6.2 认证相关错误码

| 错误码                      | HTTP状态码 | 说明                       |
| ------------------------- | ---------- | -------------------------- |
| INVALID_CREDENTIALS       | 401       | 邮箱或密码错误             |
| INVALID_REFRESH_TOKEN    | 401       | 刷新令牌无效或过期         |
| SESSION_REVOKED          | 401       | 会话已被撤销               |
| TOKEN_EXPIRED            | 401       | 访问令牌已过期             |
| USER_NOT_FOUND           | 404       | 用户不存在                 |
| SESSION_NOT_FOUND        | 404       | 会话不存在                 |
| EMAIL_ALREADY_EXISTS     | 400       | 邮箱已被注册               |
| PASSWORD_MISMATCH        | 400       | 两次密码输入不一致         |
| WEAK_PASSWORD            | 400       | 密码强度不足               |

### 6.3 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "status": "error",
  "message": "错误描述",
  "error": {
    "code": "ERROR_CODE",
    "message": "详细错误信息",
    "details": {
      "field": "错误字段",
      "value": "错误值",
      "constraint": "约束条件"
    }
  },
  "timestamp": "2026-01-12T10:30:00Z",
  "request_id": "req_123456"
}
```

---

## 7. 附录

### 7.1 Token 使用说明

#### 7.1.1 Token 类型

| Token类型        | 有效期      | 用途                           |
| ----------------- | --------- | ------------------------------ |
| Access Token     | 1小时     | API调用认证                    |
| Refresh Token    | 30天      | 刷新Access Token              |

#### 7.1.2 Token 存储建议

```javascript
// 前端存储示例
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
```

**安全注意事项**:
1. 不要在URL中传递Token
2. 使用HTTPS传输Token
3. 定期清理过期的Token
4. 避免XSS攻击窃取Token

#### 7.1.3 Token 刷新流程

```
API请求返回401
    ↓
使用refresh_token调用刷新接口
    ↓
刷新成功？
    ├─ 是 → 更新本地Token → 重试原请求
    └─ 否 → 清除本地Token → 跳转登录页
```

### 7.2 数据模型

#### 7.2.1 User 模型

| 字段           | 类型             | 说明                       |
| -------------- | ---------------- | -------------------------- |
| id             | VARCHAR(36)      | 用户唯一标识               |
| email          | VARCHAR(255)     | 用户邮箱                   |
| name           | VARCHAR(255)     | 用户名称                   |
| role           | VARCHAR(20)      | 用户角色 (USER/ADMIN)      |
| is_active      | BOOLEAN          | 账户是否激活               |
| is_superuser   | BOOLEAN          | 是否为超级用户             |
| auth_type      | VARCHAR(20)      | 认证类型 (password/saml)    |
| avatar_url     | VARCHAR(500)     | 头像URL                   |
| bio            | TEXT             | 个人简介                   |
| created_at     | TIMESTAMP        | 创建时间                   |
| last_login_at  | TIMESTAMP        | 最后登录时间               |

#### 7.2.2 UserSession 模型

| 字段               | 类型             | 说明                       |
| ------------------ | ---------------- | -------------------------- |
| id                 | VARCHAR(36)      | 会话唯一标识               |
| user_id            | VARCHAR(36)      | 关联的用户ID               |
| token_jti          | VARCHAR(255)     | JWT Token唯一标识           |
| refresh_token_jti | VARCHAR(255)     | Refresh Token唯一标识      |
| user_agent         | TEXT             | 用户代理字符串               |
| ip_address         | VARCHAR(45)      | IP地址                     |
| expires_at         | TIMESTAMP        | 访问令牌过期时间            |
| refresh_expires_at | TIMESTAMP        | 刷新令牌过期时间            |
| created_at         | TIMESTAMP        | 会话创建时间               |
| updated_at         | TIMESTAMP        | 会话最后更新时间           |
| revoked_at         | TIMESTAMP        | 会话撤销时间               |

### 7.3 接口调用示例

#### 7.3.1 使用 cURL

```bash
# 用户注册
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "张三",
    "password": "Password123",
    "confirm_password": "Password123"
  }'

# 用户登录
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Password123"
  }'

# 刷新Token
curl -X POST http://localhost:8080/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'

# 获取用户信息
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 登出
curl -X POST http://localhost:8080/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 7.3.2 使用 JavaScript (Axios)

```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080/api/v1/auth';

// 用户注册
async function register(email, name, password) {
  const response = await axios.post(`${API_BASE_URL}/register`, {
    email,
    name,
    password,
    confirm_password: password
  });
  return response.data;
}

// 用户登录
async function login(email, password) {
  const response = await axios.post(`${API_BASE_URL}/login`, {
    email,
    password
  });

  // 存储Token
  localStorage.setItem('access_token', response.data.data.access_token);
  localStorage.setItem('refresh_token', response.data.data.refresh_token);

  return response.data;
}

// 刷新Token
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  const response = await axios.post(`${API_BASE_URL}/refresh`, {
    refresh_token: refreshToken
  });

  // 更新Token（重要：refresh_token 也会更新）
  localStorage.setItem('access_token', response.data.data.access_token);
  localStorage.setItem('refresh_token', response.data.data.refresh_token);

  return response.data;
}

// 获取用户信息
async function getCurrentUser() {
  const accessToken = localStorage.getItem('access_token');
  const response = await axios.get(`${API_BASE_URL}/me`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return response.data;
}

// 登出
async function logout() {
  const accessToken = localStorage.getItem('access_token');
  await axios.post(`${API_BASE_URL}/logout`, {}, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  // 清除本地Token
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
```

### 7.4 更新日志

| 版本 | 日期       | 变更内容                                 |
| ---- | --------- | ---------------------------------------- |
| v1.0 | 2026-01-12 | 初始版本，包含所有用户认证相关接口文档 |

---

**文档结束**
