# JWT认证功能实现总结

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | JWT认证功能实现总结 |
| 创建日期 | 2025-01-12 |
| 功能模块 | 用户登录认证 |
| 文档状态 | 已完成 |

---

## 1. 功能概述

本文档总结了 AI-PPTist 系统 JWT 认证功能的实现。该功能提供了完整的用户注册、登录、Token管理和会话管理能力，为后续的 SSO 单点登录功能奠定了基础。

### 1.1 核心功能

- **用户注册**：邮箱密码注册，自动生成JWT Token
- **用户登录**：邮箱密码认证，支持暴力破解检测
- **Token刷新**：使用刷新令牌获取新的访问令牌
- **用户登出**：单设备登出和所有设备登出
- **会话管理**：查看活跃会话，撤销指定会话
- **用户信息**：获取当前登录用户信息

### 1.2 安全特性

- **密码加密**：使用 bcrypt 算法，可配置 rounds（默认12）
- **密码强度验证**：可配置密码长度、大小写、数字、特殊字符要求
- **暴力破解防护**：30分钟内5次失败尝试限制
- **会话管理**：Token 唯一标识（JTI），支持会话撤销
- **Token 过期**：访问令牌60分钟，刷新令牌30天

---

## 2. 架构设计

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      API 端点层                          │
│  处理HTTP请求/响应，参数验证，调用Handler                   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    中间件层                             │
│  认证依赖注入：get_current_user, get_current_active_user    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    Service 层                          │
│  AuthService：处理认证业务逻辑，调用Repository            │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  Repository 层                          │
│  UserRepository, UserSessionRepository, LoginHistoryRepo  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   数据模型层                             │
│  User, UserSession, LoginHistory                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| JWT Handler | `app/core/auth/jwt_handler.py` | Token生成、验证、刷新 |
| 密码 Handler | `app/core/auth/password_handler.py` | 密码哈希、验证、强度校验 |
| 认证中间件 | `app/core/middleware/auth.py` | 认证依赖注入 |
| 认证服务 | `app/services/auth/auth_service.py` | 业务逻辑处理 |
| 认证端点 | `app/api/v1/endpoints/auth.py` | API接口实现 |

---

## 3. 数据库设计

### 3.1 用户表扩展字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `auth_type` | VARCHAR(20) | 认证类型：password 或 saml |
| `saml_name_id` | VARCHAR(255) | SAML NameID，用户在IDP的唯一标识 |
| `saml_session_index` | VARCHAR(255) | SAML SessionIndex |
| `saml_attributes` | JSONB | SAML返回的用户属性 |
| `last_sso_login_at` | TIMESTAMP | 最后SSO登录时间 |

### 3.2 用户会话表 (user_sessions)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(36) | 主键 |
| `user_id` | VARCHAR(36) | 用户ID |
| `token_jti` | VARCHAR(255) | JWT Token唯一标识 |
| `refresh_token_jti` | VARCHAR(255) | 刷新Token唯一标识 |
| `user_agent` | TEXT | 用户代理 |
| `ip_address` | VARCHAR(45) | IP地址 |
| `expires_at` | TIMESTAMP | 访问令牌过期时间 |
| `refresh_expires_at` | TIMESTAMP | 刷新令牌过期时间 |
| `revoked_at` | TIMESTAMP | 撤销时间 |

### 3.3 登录历史表 (login_history)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(36) | 主键 |
| `user_id` | VARCHAR(36) | 用户ID（可为空） |
| `auth_type` | VARCHAR(20) | 认证类型 |
| `login_status` | VARCHAR(20) | 登录状态：success 或 failed |
| `failure_reason` | VARCHAR(255) | 失败原因 |
| `ip_address` | VARCHAR(45) | IP地址 |
| `user_agent` | TEXT | 用户代理 |
| `saml_name_id` | VARCHAR(255) | SAML登录时的NameID |

---

## 4. API 接口文档

### 4.1 用户登录

**接口：** `POST /api/v1/auth/login`

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应：**
```json
{
  "status": "success",
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_at": "2024-01-13T10:30:00Z",
    "refresh_expires_at": "2024-02-12T10:30:00Z",
    "user": {
      "id": "user-id-123",
      "email": "user@example.com",
      "name": "张三",
      "role": "USER",
      "is_active": true,
      "is_superuser": false,
      "auth_type": "password"
    }
  }
}
```

### 4.2 用户注册

**接口：** `POST /api/v1/auth/register`

**请求体：**
```json
{
  "email": "user@example.com",
  "name": "张三",
  "password": "Password123",
  "confirm_password": "Password123"
}
```

### 4.3 刷新Token

**接口：** `POST /api/v1/auth/refresh`

**请求体：**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 4.4 用户登出

**接口：** `POST /api/v1/auth/logout`

**认证：** 需要

### 4.5 获取当前用户信息

**接口：** `GET /api/v1/auth/me`

**认证：** 需要

### 4.6 获取用户会话列表

**接口：** `GET /api/v1/auth/sessions?skip=0&limit=20`

**认证：** 需要

### 4.7 撤销指定会话

**接口：** `POST /api/v1/auth/sessions/{session_id}/revoke`

**认证：** 需要

### 4.8 登出所有设备

**接口：** `POST /api/v1/auth/logout-all`

**认证：** 需要

---

## 5. 环境变量配置

在 `config/.env` 文件中添加以下配置：

```bash
# JWT认证配置
JWT_SECRET_KEY=your-super-secret-key-change-in-production-please-use-strong-random-key-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# 密码配置
PASSWORD_BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=false
```

---

## 6. 使用示例

### 6.1 用户登录

```python
import requests

response = requests.post(
    "http://localhost:8080/api/v1/auth/login",
    json={
        "email": "user@example.com",
        "password": "password123"
    }
)

data = response.json()["data"]
access_token = data["access_token"]
```

### 6.2 使用Token访问受保护接口

```python
headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "http://localhost:8080/api/v1/auth/me",
    headers=headers
)

user_info = response.json()["data"]
```

### 6.3 刷新Token

```python
response = requests.post(
    "http://localhost:8080/api/v1/auth/refresh",
    json={
        "refresh_token": refresh_token
    }
)

new_access_token = response.json()["data"]["access_token"]
```

---

## 7. 安全注意事项

### 7.1 生产环境配置

1. **修改 JWT_SECRET_KEY**
   ```bash
   # 使用强随机密钥（至少32位）
   JWT_SECRET_KEY=<生成的强随机密钥>
   ```

2. **调整Token过期时间**（根据安全需求）
   - 开发环境：`ACCESS_TOKEN_EXPIRE_MINUTES=60`
   - 生产环境：可调整为30分钟

3. **启用HTTPS**（生产环境必须）

### 7.2 密码安全

- 生产环境使用 `PASSWORD_BCRYPT_ROUNDS=12` 或更高
- 建议启用 `PASSWORD_REQUIRE_SPECIAL=true`

### 7.3 暴力破解防护

- 默认30分钟内5次失败尝试
- 可在 `AuthService` 中调整限制策略

---

## 8. 依赖包

已在 `backend/pyproject.toml` 中添加：

```toml
# 认证和安全
"python3-saml>=1.15.0",  # SAML 2.0 SSO认证支持
"python-jose[cryptography]>=3.3.0",  # JWT Token处理
"passlib[bcrypt]>=1.7.4",  # 密码哈希和验证
"eventlet>=0.40.0",  # Celery eventlet pool支持
"nanoid>=2.0.0",  # 唯一ID生成器
```

安装命令：
```bash
pip install python-jose[cryptography] passlib[bcrypt] eventlet nanoid
```

---

## 9. 数据库初始化

执行以下脚本创建必要的数据库表：

```bash
# 连接到数据库
psql -U ai_pptist_dev -d ai_pptist_dev

# 执行初始化脚本
\i docker/database/init-scripts/09_sso_support.sql
```

---

## 10. 测试建议

### 10.1 单元测试

- [ ] JWT Handler 测试
- [ ] 密码 Handler 测试
- [ ] AuthService 测试
- [ ] Repository 测试

### 10.2 集成测试

- [ ] 用户注册流程
- [ ] 用户登录流程
- [ ] Token刷新流程
- [ ] 登出流程
- [ ] 会话管理流程

### 10.3 安全测试

- [ ] SQL注入测试
- [ ] 暴力破解防护测试
- [ ] Token过期测试
- [ ] 会话撤销测试

---

## 11. 后续开发

### 11.1 SSO 单点登录

基于当前JWT认证架构，下一步将实现：
- SAML 2.0 协议集成
- IDP（身份提供商）对接
- 单点登出（SLO）
- 用户属性映射

### 11.2 权限管理

- 基于角色的访问控制（RBAC）
- 权限装饰器
- 资源级权限控制

### 11.3 OAuth2.0 支持

- 第三方登录集成（微信、GitHub等）
- OAuth2.0 授权码模式

---

## 12. 文件清单

### 12.1 新增文件

```
backend/app/
├── core/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py
│   │   └── password_handler.py
│   └── middleware/
│       ├── __init__.py
│       └── auth.py
├── models/
│   ├── __init__.py (更新)
│   ├── user.py
│   ├── user_session.py
│   └── login_history.py
├── repositories/
│   ├── __init__.py (更新)
│   ├── user.py
│   ├── user_session.py
│   └── login_history.py
├── schemas/
│   └── auth.py
├── services/
│   └── auth/
│       ├── __init__.py
│       └── auth_service.py
└── api/
    └── v1/
        ├── endpoints/
        │   └── auth.py
        └── router.py (更新)
```

### 12.2 修改文件

- `backend/pyproject.toml` - 添加认证依赖
- `config/.env` - 添加认证相关环境变量

---

## 13. API 使用流程

### 13.1 登录流程

```
1. 用户提交邮箱和密码
2. 验证用户凭据
3. 创建访问令牌和刷新令牌
4. 创建用户会话记录
5. 记录登录历史
6. 返回令牌和用户信息
```

### 13.2 Token刷新流程

```
1. 用户提交刷新令牌
2. 验证刷新令牌有效性
3. 检查会话是否活跃
4. 创建新的访问令牌
5. 撤销旧的访问令牌
6. 返回新的访问令牌
```

### 13.3 登出流程

```
1. 验证用户身份
2. 从token中获取JTI
3. 撤销对应的会话记录
4. 返回登出成功
```

---

## 14. 常见问题

### 14.1 Token过期后如何处理？

客户端应该在收到401错误后，使用刷新令牌调用 `/api/v1/auth/refresh` 接口获取新的访问令牌。

### 14.2 如何实现"记住我"功能？

通过延长刷新令牌的有效期来实现，可在环境变量中配置 `REFRESH_TOKEN_EXPIRE_DAYS`。

### 14.3 如何限制同时登录设备数量？

在创建新会话前，检查用户活跃会话数量，超过限制时撤销最旧的会话。

---

## 15. 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2025-01-12 | 初始版本，完成JWT认证功能 | Claude Code |

---

**文档结束**
