# AI-PPTist SSO 单点登录实现总结文档

## 文档信息

| 项目     | 内容                           |
| -------- | ------------------------------ |
| 文档名称 | AI-PPTist SSO单点登录实现总结  |
| 文档版本 | v1.0.0                         |
| 创建日期 | 2026-01-14                     |
| 项目名称 | AI-PPTist                      |
| 文档状态 | 完成                           |
| 作者     | AI Assistant                   |

---

## 目录

1. [概述](#1-概述)
2. [技术架构](#2-技术架构)
3. [后端实现](#3-后端实现)
4. [前端实现](#4-前端实现)
5. [SSO认证流程](#5-sso认证流程)
6. [配置说明](#6-配置说明)
7. [数据库设计](#7-数据库设计)
8. [安全考虑](#8-安全考虑)
9. [部署指南](#9-部署指南)
10. [故障排查](#10-故障排查)

---

## 1. 概述

### 1.1 功能说明

AI-PPTist 系统实现了基于 SAML 2.0 协议的 SSO（Single Sign-On）单点登录功能，允许用户使用企业统一身份认证系统登录，无需记忆额外的账号密码。

### 1.2 核心特性

- **SAML 2.0 协议**：使用标准 SAML 2.0 协议与 IDP（Identity Provider）通信
- **自动用户创建**：首次 SSO 登录时自动创建用户记录
- **JWT Token 认证**：使用 JWT 进行前后端认证通信
- **会话管理**：完整的会话创建、刷新、撤销机制
- **单点登出**：支持 SLO（Single Logout）全局登出
- **双认证模式**：支持账号密码登录和 SSO 登录两种方式

### 1.3 技术选型

| 组件       | 技术方案                       |
| ---------- | ------------------------------ |
| SAML 库    | python3-saml (OneLogin)        |
| JWT 处理   | python-jose[cryptography]     |
| 密码加密   | passlib[bcrypt]                |
| 会话存储   | Redis                          |
| 用户存储   | PostgreSQL                     |
| 前端状态   | Pinia (Vue 3)                  |
| HTTP 客户端 | Axios                          |

---

## 2. 技术架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI-PPTist SSO 架构                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│                  │         │                  │         │                  │
│   Vue 3 前端     │         │  FastAPI 后端    │         │  SAML IDP        │
│                  │         │                  │         │  (53jy.net)      │
│  ┌────────────┐  │         │  ┌────────────┐  │         │                  │
│  │ 登录页面    │  │         │  │ SAML SP    │  │◄───────│──│ SSO Login      │
│  │            │  │         │  │ Handler    │  │         │                  │
│  └──────┬─────┘  │         │  └──────┬─────┘  │         │  ┌────────────┐  │
│         │         │         │         │         │         │  │ 用户认证    │  │
│         │         │         │         │         │         │  │            │  │
│  ┌──────▼─────┐  │         │  ┌──────▼─────┐  │         │  └────────────┘  │
│  │ Auth Store │  │         │  │ 认证中间件 │  │         │                  │
│  │ (Pinia)    │  │         │  │            │  │         │                  │
│  └────────────┘  │         │  └──────┬─────┘  │         │                  │
│                  │         │         │         │         │                  │
│  ┌────────────┐  │         │  ┌──────▼─────┐  │         │                  │
│  │ HTTP拦截器 │  │         │  │ 用户管理   │  │         │                  │
│  │            │  │         │  │ Repository │  │         │                  │
│  └────────────┘  │         │  └──────┬─────┘  │         │                  │
│                  │         │         │         │         │                  │
│                  │         │  ┌──────▼─────┐  │         │                  │
│                  │         │  │ PostgreSQL │  │         │                  │
│                  │         │  │   用户表   │  │         │                  │
│                  │         │  └────────────┘  │         │                  │
│                  │         │                  │         │                  │
│                  │         │  ┌────────────┐  │         │                  │
│                  │         │  │   Redis    │  │         │                  │
│                  │         │  │ 会话存储   │  │         │                  │
│                  │         │  └────────────┘  │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
```

### 2.2 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                           │
├─────────────────────────────────────────────────────────────────┤
│  视图层 (Views)          │  组件层 (Components)                │
│  - LoginPage             │  - LoginForm                        │
│  - SSOCallbackPage       │  - SSOButton                        │
├─────────────────────────────────────────────────────────────────┤
│  状态管理层 (Pinia)      │  服务层 (Services)                   │
│  - useAuthStore          │  - authService                      │
│  - 用户状态、Token管理   │  - API调用封装                       │
├─────────────────────────────────────────────────────────────────┤
│  工具层                  │  类型层 (Types)                      │
│  - HTTP拦截器            │  - User, TokenResponse等             │
│  - Token工具函数         │                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      后端层 (FastAPI)                           │
├─────────────────────────────────────────────────────────────────┤
│  端点层 (Endpoints)      │  处理器层 (Handlers)                 │
│  - /auth/sso/init        │  - SAML请求处理                      │
│  - /auth/sso/acs         │  - SAML响应解析                      │
│  - /auth/sso/slo         │  - 用户验证                          │
├─────────────────────────────────────────────────────────────────┤
│  服务层 (Services)       │  核心层 (Core)                        │
│  - SAMLAuthService       │  - SAML配置加载                      │
│  - AuthService           │  - JWT处理                           │
│  - 业务逻辑封装           │  - 密码加密                          │
├─────────────────────────────────────────────────────────────────┤
│  仓库层 (Repositories)    │  数据层 (Data)                       │
│  - UserRepository        │  - PostgreSQL                        │
│  - UserSessionRepository  │  - Redis                             │
│  - LoginHistoryRepository │                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 后端实现

### 3.1 目录结构

```
backend/app/
├── api/v1/endpoints/
│   ├── auth.py              # 认证端点（登录、注册等）
│   └── auth_sso.py          # SSO专用端点
├── core/
│   ├── auth/
│   │   ├── jwt_handler.py   # JWT Token处理
│   │   └── password_handler.py  # 密码加密验证
│   ├── config/
│   │   └── saml_config.py   # SAML配置加载器
│   ├── exceptions/
│   │   └── saml.py          # SAML异常定义
│   └── middleware/
│       └── auth.py          # 认证中间件
├── schemas/
│   ├── auth.py              # 认证相关Schema
│   └── auth_sso.py          # SSO专用Schema
├── services/
│   └── auth/
│       ├── auth_service.py  # 认证服务
│       └── saml_auth_service.py  # SAML认证服务
├── repositories/
│   ├── user.py              # 用户数据访问
│   ├── user_session.py      # 会话数据访问
│   └── login_history.py     # 登录历史访问
└── saml/                    # SAML配置文件目录
    ├── settings.json        # SAML基础配置
    ├── advanced_settings.json  # SAML高级配置
    └── certs/               # 证书目录
        ├── sp.key           # SP私钥
        └── sp.crt           # SP证书
```

### 3.2 核心模块详解

#### 3.2.1 SAML配置加载器 (`saml_config.py`)

**功能**：负责加载和管理 SAML 配置，支持从配置文件和环境变量加载。

**核心类**：
- `SAMLConfigLoader`：配置加载器类
- `SAMLSettings`：Pydantic设置类

**关键特性**：
- 环境变量占位符替换 (`${VARIABLE_NAME}`)
- 配置缓存机制
- 多路径环境变量文件加载
- 默认配置构建

**配置加载流程**：
```python
1. 尝试从 saml/settings.json 加载配置
2. 如果文件不存在，从环境变量构建默认配置
3. 递归替换配置中的 ${VAR_NAME} 占位符
4. 缓存配置结果
```

**环境变量配置**：
```bash
# SP (Service Provider) 配置
SAML_SP_ENTITY_ID=http://localhost:8080/api/v1/auth/metadata
SAML_ACS_URL=http://localhost:8080/api/v1/auth/sso/acs
SAML_SLS_URL=http://localhost:8080/api/v1/auth/sso/slo
SAML_SP_CERT=<SP证书内容>
SAML_SP_KEY=<SP私钥内容>

# IDP (Identity Provider) 配置
SAML_IDP_ENTITY_ID=<IDP实体ID>
SAML_IDP_SSO_URL=<IDP单点登录URL>
SAML_IDP_SLS_URL=<IDP单点登出URL>
SAML_IDP_CERT=<IDP证书内容>

# 安全选项
SAML_STRICT=true
SAML_DEBUG=true
```

#### 3.2.2 SAML认证服务 (`saml_auth_service.py`)

**功能**：处理 SAML SSO 业务逻辑，包括登录、用户创建、会话管理。

**核心方法**：

| 方法名                      | 功能说明                           |
| --------------------------- | ---------------------------------- |
| `initiate_sso_login()`      | 发起SSO登录，返回IdP登录URL        |
| `process_acs_response()`    | 处理SAML响应，完成用户认证         |
| `initiate_slo()`            | 发起单点登出                       |
| `process_slo_response()`    | 处理SLO响应                        |
| `get_sp_metadata()`         | 获取SP元数据XML                    |
| `_extract_email()`          | 从SAML属性中提取邮箱               |
| `_extract_name()`           | 从SAML属性中提取姓名               |
| `_get_or_create_sso_user()` | 获取或创建SSO用户                  |

**用户创建逻辑**：
```python
1. 尝试通过 saml_name_id 查找用户
   └─ 找到 → 更新SAML信息
2. 尝试通过 email 查找用户
   └─ 找到 → 更新为SSO用户
3. 都未找到 → 创建新的SSO用户
```

**SAML属性提取规则**：
- 邮箱：依次尝试 `email`、`Email`、`mail`、`EmailAddress` 等属性
- 姓名：依次尝试 `displayName`、`name`、`cn`、`commonName` 等属性
- 回退：使用 NameID 作为默认值

#### 3.2.3 SSO端点 (`auth_sso.py`)

**功能**：提供 SAML SSO 相关的 HTTP 端点。

| 端点              | 方法 | 功能                           |
| ----------------- | ---- | ------------------------------ |
| `/auth/sso/init`  | POST | 发起SSO登录，返回IdP登录URL    |
| `/auth/sso/acs`   | POST | 处理SAML响应（Assertion Consumer Service） |
| `/auth/sso/acs`   | GET  | 处理SAML响应（GET方法）         |
| `/auth/sso/slo`   | POST | 发起单点登出                   |
| `/auth/sso/sls`   | GET  | 处理SLO响应                    |
| `/auth/sso/metadata` | GET | 获取SP元数据XML                |

**重要实现细节**：

1. **init端点**：
   - 返回JSON而非302重定向（避免CORS问题）
   - 前端使用 `window.location.href` 进行跳转

2. **acs端点**：
   - 支持POST和GET两种方法
   - 从URL参数获取RelayState（用于重定向）
   - 使用URL参数传递token（避免跨域localStorage问题）
   - 自动重定向到前端回调页面

3. **Token传递方式**：
```python
# 将token添加到重定向URL的查询参数中
query_params = {
    'access_token': sso_response['access_token'],
    'refresh_token': sso_response['refresh_token'],
}
final_redirect_url = urlunparse(parsed_url._replace(query=urlencode(query_params)))
```

#### 3.2.4 JWT处理器 (`jwt_handler.py`)

**功能**：JWT Token 的创建、验证和解析。

**核心方法**：
- `create_token_pair()`：创建访问令牌和刷新令牌对
- `decode_token()`：解码并验证JWT
- `get_token_jti()`：获取Token的JWT ID
- `verify_token()`：验证Token有效性

**Token配置**：
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60   # 访问令牌1小时过期
REFRESH_TOKEN_EXPIRE_DAYS = 30      # 刷新令牌30天过期
ALGORITHM = "HS256"                 # 签名算法
```

**Token Payload结构**：
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "USER",
  "jti": "unique_token_id",
  "exp": 1234567890,
  "iat": 1234567890
}
```

#### 3.2.5 认证中间件 (`auth.py`)

**功能**：提供认证依赖注入，保护需要认证的API端点。

**核心函数**：
- `get_current_user()`：获取当前认证用户
- `get_current_active_user()`：获取当前活跃用户

**使用方式**：
```python
@router.get("/protected")
async def protected_endpoint(
    current_user: dict = Depends(get_current_user)
):
    return {"user_id": current_user["id"]}
```

### 3.3 数据访问层

#### 3.3.1 用户仓库 (`user.py`)

**核心方法**：

| 方法名                  | 功能说明                     |
| ----------------------- | ---------------------------- |
| `get_by_email()`        | 通过邮箱查找用户             |
| `get_by_saml_name_id()` | 通过SAML NameID查找用户      |
| `create_sso_user()`     | 创建SSO用户                  |
| `update_saml_info()`    | 更新用户SAML信息             |
| `update_last_login()`   |更新最后登录时间              |

#### 3.3.2 会话仓库 (`user_session.py`)

**核心方法**：

| 方法名              | 功能说明                 |
| ------------------- | ------------------------ |
| `create_session()`  | 创建用户会话记录         |
| `get_by_token_jti()` | 通过Token JTI查找会话    |
| `revoke_session()`  | 撤销指定会话             |
| `revoke_all_sessions()` | 撤销用户所有会话       |

---

## 4. 前端实现

### 4.1 目录结构

```
frontend/src/
├── views/
│   ├── Login/             # 登录页面
│   │   ├── index.vue      # 登录页面主组件
│   │   └── components/
│   │       ├── LoginForm.vue      # 账号密码登录表单
│   │       └── SSOButton.vue      # SSO登录按钮
│   └── SSOCallback/       # SSO回调页面
│       └── index.vue
├── store/
│   └── auth.ts            # 认证状态管理 (Pinia)
├── services/
│   └── authService.ts     # 认证API服务
├── types/
│   └── auth.ts            # 认证类型定义
├── configs/
│   └── api.ts             # API端点配置
└── router/
    └── index.ts           # 路由配置和守卫
```

### 4.2 核心模块详解

#### 4.2.1 认证Store (`auth.ts`)

**功能**：使用 Pinia 管理认证状态。

**State结构**：
```typescript
interface AuthState {
  accessToken: string | null    // 访问令牌
  refreshToken: string | null   // 刷新令牌
  user: User | null             // 当前用户信息
  isLoading: boolean            // 加载状态
}
```

**Getters**：
- `isAuthenticated`：是否已登录
- `userDisplayName`：用户显示名称
- `userRole`：用户角色
- `isAdmin`：是否为管理员
- `authType`：认证类型（password/saml）

**Actions**：

| 方法名                  | 功能说明                           |
| ----------------------- | ---------------------------------- |
| `login()`               | 账号密码登录                       |
| `initiateSSOLogin()`    | 发起SSO登录                        |
| `handleSSOCallback()`   | 处理SSO回调                         |
| `register()`            | 用户注册                           |
| `refreshAccessToken()`  | 刷新访问令牌                       |
| `fetchCurrentUser()`    | 获取当前用户信息                   |
| `logout()`              | 用户登出                           |
| `clearAuth()`           | 清除认证状态                       |
| `initAuth()`            | 初始化认证状态（从本地存储恢复）   |

#### 4.2.2 认证服务 (`authService.ts`)

**功能**：封装所有认证相关的API调用。

**核心方法**：

| 方法名               | 功能说明                           | API端点                      |
| -------------------- | ---------------------------------- | --------------------------- |
| `login()`            | 账号密码登录                       | `POST /api/v1/auth/login`   |
| `register()`         | 用户注册                           | `POST /api/v1/auth/register`|
| `initiateSSO()`      | 发起SSO登录                        | `POST /api/v1/auth/sso/init`|
| `handleSSOCallback()` | 处理SSO回调                        | 本地处理                    |
| `logout()`           | 用户登出                           | `POST /api/v1/auth/logout`  |
| `refreshToken()`     | 刷新访问令牌                       | `POST /api/v1/auth/refresh` |
| `getCurrentUser()`   | 获取当前用户信息                   | `GET /api/v1/auth/me`       |
| `getSessions()`      | 获取会话列表                       | `GET /api/v1/auth/sessions` |

**Token管理**：
```typescript
// LocalStorage键名
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user',
}

// 保存Token
function saveTokens(accessToken: string, refreshToken: string): void

// 获取Token
function getAccessToken(): string | null
function getRefreshToken(): string | null

// 清除Token
function clearTokens(): void
```

**SSO回调处理逻辑**：
```typescript
1. 尝试从localStorage获取token（后端已保存）
   ├─ 成功 → 验证token有效性
   └─ 失败 → 继续下一步
2. 尝试从URL参数获取token（备用方案）
   ├─ 成功 → 保存token并获取用户信息
   └─ 失败 → 返回null
3. 清除URL中的token参数（安全考虑）
```

#### 4.2.3 类型定义 (`auth.ts`)

**核心类型**：

```typescript
// 用户信息
interface User {
  id: string
  email: string
  name: string
  role: 'USER' | 'ADMIN'
  is_active: boolean
  is_superuser: boolean
  auth_type: 'password' | 'saml'
  avatar_url: string | null
  bio: string | null
  created_at: string
  last_login_at: string
}

// Token响应
interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_at: string
  refresh_expires_at: string
  user: User
}

// 标准API响应
interface StandardResponse<T> {
  status: 'success' | 'error'
  message: string
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
  timestamp: string
  request_id: string
}
```

#### 4.2.4 HTTP拦截器配置

**请求拦截器**：
```typescript
// 自动添加Authorization头部
instance.interceptors.request.use(
  config => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  }
)
```

**响应拦截器**：
```typescript
// 处理401错误，自动刷新Token
instance.interceptors.response.use(
  response => response.data,
  async error => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await authStore.refreshAccessToken()
        const newToken = getAccessToken()
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return instance(originalRequest)
      } catch {
        await authStore.logout()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

#### 4.2.5 路由守卫

**全局前置守卫**：
```typescript
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 需要认证的页面
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      const token = getAccessToken()
      if (token) {
        try {
          await authStore.fetchCurrentUser()
          next()
          return
        } catch {
          next({ name: 'Login', query: { redirect: to.fullPath } })
          return
        }
      } else {
        next({ name: 'Login', query: { redirect: to.fullPath } })
        return
      }
    }
  }

  // 已登录用户访问登录页
  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Home' })
    return
  }

  next()
})
```

### 4.3 页面组件

#### 4.3.1 登录页面 (`Login/index.vue`)

**功能**：提供账号密码登录和SSO登录两种方式。

**核心功能**：
- 表单验证（邮箱格式、密码强度）
- 错误提示
- 加载状态
- 记住我功能
- SSO登录按钮

**SSO登录流程**：
```typescript
async function handleSSOLogin() {
  ssoLoading.value = true
  try {
    // 1. 调用后端init端点获取IdP URL
    // 2. 跳转到IdP登录页面
    await authStore.initiateSSOLogin(returnToUrl)
  } catch (error) {
    console.error('SSO登录失败:', error)
  } finally {
    ssoLoading.value = false
  }
}
```

#### 4.3.2 SSO回调页面 (`SSOCallback/index.vue`)

**功能**：处理SSO登录后的回调，完成认证流程。

**处理流程**：
```typescript
onMounted(async () => {
  try {
    // 1. 从URL参数或localStorage获取token
    const response = await authStore.handleSSOCallback()

    if (response && response.user) {
      // 2. 登录成功，跳转到主页或原始访问页面
      const redirect = route.query.redirect as string || '/'
      await router.push(redirect)
    } else {
      // 3. 未获取到token，返回登录页
      await router.push('/login')
    }
  } catch (error) {
    console.error('SSO回调处理失败:', error)
    await router.push('/login')
  }
})
```

---

## 5. SSO认证流程

### 5.1 完整SSO登录时序图

```
┌───────┐         ┌─────────┐         ┌──────────┐         ┌─────────┐
│ 用户  │         │ 前端    │         │ 后端     │         │  IDP    │
└───────┘         └─────────┘         └──────────┘         └─────────┘
   │                 │                   │                    │
   │ 访问页面         │                   │                    │
   ├────────────────►│                   │                    │
   │                 │                   │                    │
   │                 │ 检查登录状态       │                    │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │ 未认证             │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │ 重定向到登录页   │                   │                    │
   │◄────────────────┤                   │                    │
   │                 │                   │                    │
   │ 点击SSO登录      │                   │                    │
   ├────────────────►│                   │                    │
   │                 │                   │                    │
   │                 │ POST /auth/sso/init│                   │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │                   │ 生成SAML AuthNRequest
   │                 │                   │                    │
   │                 │                   │ ├──────────────────►│
   │                 │                   │                    │
   │                 │                   │    302 + IdP URL   │
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │ JSON {redirect_url}│                   │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  跳转到IdP       │                   │                    │
   ├─────────────────────────────────────────────────────────►│
   │                 │                   │                    │
   │                 │                   │              用户登录
   │                 │                   │                    │
   │                 │                   │                    │
   │                 │                   │   SAML Response     │
   │                 │                   │◄──────────────────┤
   │                 │                   │    (POST to ACS)   │
   │                 │                   │                    │
   │                 │                   │  验证Response       │
   │                 │                   │  提取用户属性       │
   │                 │                   │                    │
   │                 │                   │  创建/更新用户      │
   │                 │                   │  生成JWT Token      │
   │                 │                   │                    │
   │                 │                   │  存储会话到Redis    │
   │                 │                   │                    │
   │                 │                   │  302 + Token (URL)  │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  重定向到前端     │                   │                    │
   │◄────────────────┤                   │                    │
   │                 │                   │                    │
   │  从URL获取Token  │                   │                    │
   │  存储到localStorage│                  │                    │
   │  验证Token       │                   │                    │
   │                 │                   │                    │
   │                 │ GET /auth/me     │                    │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │ 用户信息          │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  跳转到主页       │                   │                    │
   ├────────────────►│                   │                    │
```

### 5.2 SSO登录详细步骤

#### 步骤1：发起SSO登录

**前端操作**：
```typescript
// 用户点击SSO登录按钮
await authStore.initiateSSOLogin(returnToUrl)
```

**后端处理**：
```python
# 1. 初始化SAML认证对象
auth = await self.init_saml_auth(request)

# 2. 生成SAML AuthNRequest
login_url = auth.login(return_to=return_to)

# 3. 返回IdP登录URL
return JSONResponse({
    "status": "success",
    "data": {"redirect_url": login_url}
})
```

**前端跳转**：
```typescript
// 使用window.location.href跳转到IdP
window.location.href = response.data.redirect_url
```

#### 步骤2：IdP认证

**用户操作**：
1. 在IdP登录页面输入企业账号密码
2. IdP验证用户身份
3. IdP生成SAML Response

#### 步骤3：处理SAML响应

**后端处理**：
```python
# 1. 初始化SAML认证对象
auth = await self.init_saml_auth(request)

# 2. 处理SAML Response
auth.process_response(request_id=None)

# 3. 验证Response
errors = auth.get_errors()
if errors:
    raise SAMLValidationError(...)

# 4. 提取用户信息
saml_name_id = auth.get_nameid()
saml_session_index = auth.get_session_index()
saml_attributes = auth.get_attributes()

# 5. 创建或获取用户
user = await self._get_or_create_sso_user(
    email=user_email,
    name=user_name,
    saml_name_id=saml_name_id,
    saml_session_index=saml_session_index,
    saml_attributes=saml_attributes
)

# 6. 生成JWT Token
token_data = jwt_handler.create_token_pair(
    user_id=user.id,
    additional_claims={
        "email": user.email,
        "role": user.role
    }
)

# 7. 创建会话记录
await self.session_repo.create_session(
    user_id=user.id,
    token_jti=token_data["access_jti"],
    refresh_token_jti=token_data["refresh_jti"],
    expires_at=token_data["expires_at"],
    refresh_expires_at=token_data["refresh_expires_at"],
    user_agent=user_agent,
    ip_address=ip_address
)

# 8. 重定向到前端（带Token）
return RedirectResponse(
    url=f"{redirect_url}?access_token={token}&refresh_token={refresh_token}",
    status_code=302
)
```

#### 步骤4：前端完成登录

**前端处理**：
```typescript
// 1. 从URL获取Token
const urlParams = new URLSearchParams(window.location.search)
const accessToken = urlParams.get('access_token')
const refreshToken = urlParams.get('refresh_token')

// 2. 保存Token
saveTokens(accessToken, refreshToken)

// 3. 验证Token并获取用户信息
const user = await getCurrentUser()

// 4. 更新状态
authStore.user = user
authStore.accessToken = accessToken
authStore.refreshToken = refreshToken

// 5. 清除URL中的Token参数
window.history.replaceState({}, '', window.location.pathname)

// 6. 跳转到主页
router.push(redirectUrl || '/')
```

### 5.3 单点登出（SLO）流程

```
┌───────┐         ┌─────────┐         ┌──────────┐         ┌─────────┐
│ 用户  │         │ 前端    │         │ 后端     │         │  IDP    │
└───────┘         └─────────┘         └──────────┘         └─────────┘
   │                 │                   │                    │
   │ 点击登出         │                   │                    │
   ├────────────────►│                   │                    │
   │                 │                   │                    │
   │                 │ POST /auth/sso/slo│                    │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │                   │ 撤销本地会话       │
   │                 │                   │                    │
   │                 │                   │ 生成SAML LogoutRequest
   │                 │                   │                    │
   │                 │                   │ ├──────────────────►│
   │                 │                   │                    │
   │                 │                   │    302 + IdP URL   │
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │ 清除本地Token     │                    │
   │                 │                   │                    │
   │  跳转到IdP登出   │                   │                    │
   ├─────────────────────────────────────────────────────────►│
   │                 │                   │                    │
   │                 │                   │  SAML LogoutResponse│
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │                   │ GET /auth/sso/sls  │
   │                 │                   │ ├──────────────────►│
   │                 │                   │                    │
   │                 │                   │ 处理LogoutResponse  │
   │                 │                   │                    │
   │                 │ 登出成功           │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  跳转到登录页     │                   │                    │
   ├────────────────►│                   │                    │
```

---

## 6. 配置说明

### 6.1 环境变量配置

在 `config/.env` 文件中配置以下环境变量：

```bash
# ==================== SAML SP 配置 ====================
# SP Entity ID（SP的唯一标识符）
SAML_SP_ENTITY_ID=http://localhost:8080/api/v1/auth/metadata

# ACS URL（Assertion Consumer Service，接收SAML响应的端点）
SAML_ACS_URL=http://localhost:8080/api/v1/auth/sso/acs

# SLS URL（Single Logout Service，处理登出的端点）
SAML_SLS_URL=http://localhost:8080/api/v1/auth/sso/slo

# SP 证书（用于签名SAML请求）
SAML_SP_CERT=<SP证书内容，去除换行符>

# SP 私钥（用于签名SAML请求）
SAML_SP_KEY=<SP私钥内容，去除换行符>

# ==================== SAML IDP 配置 ====================
# IDP Entity ID（IDP的唯一标识符）
SAML_IDP_ENTITY_ID=<IDP实体ID>

# IDP SSO URL（IDP的单点登录URL）
SAML_IDP_SSO_URL=<IDP单点登录URL>

# IDP SLS URL（IDP的单点登出URL）
SAML_IDP_SLS_URL=<IDP单点登出URL>

# IDP 证书（用于验证IDP签名）
SAML_IDP_CERT=<IDP证书内容>

# ==================== SAML 安全选项 ====================
# 严格模式（true：严格验证SAML响应）
SAML_STRICT=true

# 调试模式（true：输出详细日志）
SAML_DEBUG=true

# ==================== JWT 配置 ====================
# JWT密钥（用于签名JWT Token）
JWT_SECRET_KEY=your-secret-key-change-in-production

# JWT算法（HS256或RS256）
JWT_ALGORITHM=HS256

# 访问令牌过期时间（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=60

# 刷新令牌过期时间（天）
REFRESH_TOKEN_EXPIRE_DAYS=30

# ==================== 密码配置 ====================
# bcrypt加密轮数
PASSWORD_BCRYPT_ROUNDS=12
```

### 6.2 证书配置

#### 6.2.1 生成SP证书

```bash
# 生成SP私钥
openssl genrsa -out sp.key 2048

# 生成SP证书（有效期10年）
openssl req -new -x509 -key sp.key -out sp.crt -days 3650 \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=MyCompany/CN=ai-pptist-sp"

# 将证书和私钥复制到配置目录
cp sp.key backend/saml/certs/
cp sp.crt backend/saml/certs/

# 转换证书为环境变量格式（去除换行符）
cat sp.crt | tr -d '\n' > sp_cert.txt
cat sp.key | tr -d '\n' > sp_key.txt

# 将内容复制到 .env 文件
# SAML_SP_CERT=$(cat sp_cert.txt)
# SAML_SP_KEY=$(cat sp_key.txt)
```

#### 6.2.2 获取IDP证书

从IDP提供商获取以下信息：
- IDP Entity ID
- IDP SSO URL
- IDP SLS URL
- IDP X.509证书（用于验证SAML响应签名）

### 6.3 前端配置

在 `frontend/src/configs/api.ts` 中配置API端点：

```typescript
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    LOGOUT: '/api/v1/auth/logout',
    REFRESH: '/api/v1/auth/refresh',
    ME: '/api/v1/auth/me',
    SESSIONS: '/api/v1/auth/sessions',
    REVOKE_SESSION: (id: string) => `/api/v1/auth/sessions/${id}/revoke`,
    LOGOUT_ALL: '/api/v1/auth/logout-all',
    SSO_INIT: '/api/v1/auth/sso/init',
  }
}
```

在 `.env` 文件中配置环境变量：

```bash
# API基础URL
VITE_API_BASE_URL=http://localhost:8080
```

---

## 7. 数据库设计

### 7.1 users表扩展

为支持SSO登录，users表新增了以下字段：

```sql
-- 认证类型（password 或 saml）
ALTER TABLE users ADD COLUMN auth_type VARCHAR(20) DEFAULT 'password';

-- SAML NameID（用户在IDP的唯一标识）
ALTER TABLE users ADD COLUMN saml_name_id VARCHAR(255);

-- SAML SessionIndex
ALTER TABLE users ADD COLUMN saml_session_index VARCHAR(255);

-- SAML返回的用户属性（JSON格式）
ALTER TABLE users ADD COLUMN saml_attributes JSONB DEFAULT '{}'::jsonb;

-- 最后一次SSO登录时间
ALTER TABLE users ADD COLUMN last_sso_login_at TIMESTAMP WITH TIME ZONE;

-- 添加索引
CREATE INDEX idx_users_auth_type ON users(auth_type);
CREATE INDEX idx_users_saml_name_id ON users(saml_name_id);
```

### 7.2 user_sessions表

用于存储用户会话信息：

```sql
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_jti VARCHAR(255) UNIQUE,
    user_agent TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    refresh_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
```

### 7.3 login_history表

用于记录登录历史：

```sql
CREATE TABLE IF NOT EXISTS login_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    auth_type VARCHAR(20) NOT NULL,
    login_status VARCHAR(20) NOT NULL,
    failure_reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    saml_name_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_login_history_user_id ON login_history(user_id);
CREATE INDEX idx_login_history_auth_type ON login_history(auth_type);
CREATE INDEX idx_login_history_status ON login_history(login_status);
```

### 7.4 用户数据流程

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户数据流程                               │
└─────────────────────────────────────────────────────────────────┘

SSO登录触发
    │
    ▼
提取SAML属性（NameID, Email, Name等）
    │
    ▼
查找用户
    │
    ├─ 通过 saml_name_id 查找 ──────┐
    │                              │
    ├─ 通过 email 查找 ────────┐   │
    │                          │   │
    ▼                          ▼   ▼
   找到       找到（非SSO）     未找到
    │            │              │
    │            ▼              ▼
    │       更新为SSO用户    创建SSO用户
    │            │              │
    ▼            ▼              ▼
更新SAML信息   更新SAML信息   设置auth_type='saml'
    │            │              │
    └────────────┴──────────────┘
                    │
                    ▼
            生成JWT Token
                    │
                    ▼
            创建会话记录
                    │
                    ▼
            记录登录历史
                    │
                    ▼
            返回用户信息和Token
```

---

## 8. 安全考虑

### 8.1 SAML安全

**签名验证**：
- 所有SAML响应必须使用IDP证书验证签名
- 使用严格模式确保所有必填字段存在

**时间验证**：
- 验证SAML响应的有效期（NotBefore/NotOnOrAfter）
- 时钟偏移容忍：默认5分钟

**重放攻击防护**：
- 验证SAML响应的InResponseTo字段
- 存储已处理的AuthNRequest ID（TODO：使用Redis）

** Audience和Recipient验证**：
- 验证Audience限制
- 验证Recipient地址

### 8.2 Token安全

**JWT签名**：
- 使用HS256或RS256算法签名
- 密钥定期轮换

**Token有效期**：
- Access Token：1小时
- Refresh Token：30天
- 支持主动撤销

**Token存储**：
- 前端使用localStorage存储（可考虑使用HttpOnly Cookie）
- 后端使用Redis存储会话信息

**Token传递**：
- Authorization头部传递（Bearer Token）
- SSO回调使用URL参数传递（临时方案）

### 8.3 密码安全

**加密存储**：
- 使用bcrypt算法
- Cost factor >= 12

**密码策略**：
- 最小长度：8个字符
- 建议包含大小写字母和数字

### 8.4 传输安全

**HTTPS**：
- 生产环境强制使用HTTPS
- 防止中间人攻击

**CORS**：
- 配置允许的跨域来源
- 仅允许可信的前端域名

**安全头部**：
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Content-Security-Policy

### 8.5 会话管理

**会话隔离**：
- 每个用户独立的会话记录
- 支持多设备登录管理

**会话过期**：
- Access Token过期后自动刷新
- Refresh Token过期需重新登录

**会话撤销**：
- 支持撤销单个会话
- 支持撤销所有会话（登出所有设备）

---

## 9. 部署指南

### 9.1 开发环境部署

#### 9.1.1 后端部署

```bash
# 1. 配置环境变量
cd config
cp .env.example .env
# 编辑 .env 文件，配置SAML和JWT相关变量

# 2. 准备SAML证书
cd ../backend/saml/certs
# 生成SP证书（参考 6.2.1 节）
# 或使用demo-flask项目的证书

# 3. 安装依赖
cd ../../
pip install -r requirements.txt

# 4. 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

#### 9.1.2 前端部署

```bash
# 1. 配置环境变量
cd frontend
cp .env.example .env
# 编辑 .env 文件，配置API_BASE_URL

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

### 9.2 生产环境部署

#### 9.2.1 Docker部署

使用 `docker-compose.yml` 部署：

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - SAML_SP_ENTITY_ID=${SAML_SP_ENTITY_ID}
      - SAML_ACS_URL=${SAML_ACS_URL}
      - SAML_SLS_URL=${SAML_SLS_URL}
      - SAML_SP_CERT=${SAML_SP_CERT}
      - SAML_SP_KEY=${SAML_SP_KEY}
      - SAML_IDP_ENTITY_ID=${SAML_IDP_ENTITY_ID}
      - SAML_IDP_SSO_URL=${SAML_IDP_SSO_URL}
      - SAML_IDP_SLS_URL=${SAML_IDP_SLS_URL}
      - SAML_IDP_CERT=${SAML_IDP_CERT}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    volumes:
      - ./backend/saml:/app/saml
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=${API_BASE_URL}

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ai_pptist
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 9.2.2 部署步骤

```bash
# 1. 构建并启动服务
docker-compose up -d

# 2. 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 3. 查看日志
docker-compose logs -f backend

# 4. 检查服务状态
docker-compose ps
```

### 9.3 IDP配置

#### 9.3.1 获取SP元数据

```bash
# 调用后端端点获取SP元数据
curl http://localhost:8080/api/v1/auth/sso/metadata \
  --output metadata.xml
```

#### 9.3.2 配置IDP

将SP元数据提供给IDP管理员，配置信任关系：

1. 在IDP注册新的SP（Service Provider）
2. 上传SP元数据文件（metadata.xml）
3. 配置以下信息：
   - SP Entity ID：`http://your-domain.com/api/v1/auth/metadata`
   - ACS URL：`http://your-domain.com/api/v1/auth/sso/acs`
   - SLS URL：`http://your-domain.com/api/v1/auth/sso/slo`
4. 获取IDP配置信息（Entity ID、SSO URL、SLS URL、证书）
5. 配置到后端环境变量

---

## 10. 故障排查

### 10.1 常见问题

#### 问题1：SAML验证失败

**症状**：SSO登录时显示"SAML认证失败"

**排查步骤**：
1. 检查IDP配置是否正确
2. 检查SP证书是否正确配置
3. 检查IDP证书是否正确配置
4. 检查ACS URL是否正确
5. 查看后端日志：`SAML_VALIDATION_ERROR`

**解决方案**：
- 确认IDP配置与SP配置匹配
- 重新生成并配置证书
- 检查网络连接和防火墙设置

#### 问题2：Token无法传递到前端

**症状**：SSO登录后前端未收到Token

**排查步骤**：
1. 检查后端ACS端点的重定向URL
2. 检查URL长度限制（Token很长可能导致URL截断）
3. 检查前端SSO回调页面的处理逻辑
4. 查看浏览器控制台和网络请求

**解决方案**：
- 使用POST方式传递Token（需要后端返回HTML页面）
- 实现Token中转机制（后端临时存储到Redis）
- 缩短Token长度（减少Payload）

#### 问题3：用户自动创建失败

**症状**：SSO登录时无法创建用户

**排查步骤**：
1. 检查SAML属性映射是否正确
2. 检查邮箱字段是否正确提取
3. 检查数据库连接
4. 查看后端日志中的错误信息

**解决方案**：
- 调整属性提取逻辑（`_extract_email`、`_extract_name`）
- 确保数据库表结构正确
- 检查用户邮箱是否已存在冲突

#### 问题4：刷新Token失败

**症状**：Access Token过期后无法刷新

**排查步骤**：
1. 检查Refresh Token是否存在
2. 检查Refresh Token是否过期
3. 检查会话是否被撤销
4. 查看后端日志中的错误信息

**解决方案**：
- 确保Refresh Token正确存储
- 延长Refresh Token有效期
- 检查会话管理逻辑

### 10.2 调试技巧

#### 10.2.1 启用调试模式

```bash
# 后端启用SAML调试
SAML_DEBUG=true

# 查看详细SAML日志
docker-compose logs -f backend | grep SAML
```

#### 10.2.2 检查SAML配置

```python
# 在后端代码中添加调试输出
from app.core.config.saml_config import saml_settings

# 打印SAML配置
import json
settings_dict = saml_settings.load_saml_config()
print(json.dumps(settings_dict, indent=2))
```

#### 10.2.3 验证Token

```bash
# 使用jwt.io解码和验证JWT Token
# 或使用命令行工具
echo "your_jwt_token" | jq -R 'split(".") | .[1] | @base64d | fromjson'
```

### 10.3 日志分析

#### 10.3.1 SAML流程日志

```python
[SSO-ACS-START] 开始处理SAML ACS响应
[SSO-ACS-SUCCESS] SAML用户认证成功 - NameID: user@example.com
[SSO-ACS-ATTRIBUTES] SAML属性: {'email': ['user@example.com'], 'displayName': ['张三']}
[SSO-ACS-USER-INFO] 提取用户信息 - email: user@example.com, name: 张三
[SSO-ACS-GET-USER] 开始获取或创建SSO用户 - email: user@example.com
[SSO-ACS-USER-DONE] 用户处理完成 - user_id: xxx, email: user@example.com, auth_type: saml
[SSO-ACS-TOKEN-START] 开始创建JWT Token - user_id: xxx
[SSO-ACS-TOKEN-DONE] JWT Token创建成功 - access_jti: xxx, refresh_jti: xxx
[SSO-ACS-SESSION-START] 开始创建会话记录
[SSO-ACS-SESSION-DONE] 会话记录创建成功
[SSO-ACS-COMPLETE] SSO用户登录成功 - email: user@example.com, user_id: xxx
```

#### 10.3.2 前端日志

```javascript
[SSO-Callback] 开始处理SSO回调
[SSO-Callback] localStorage状态检查:
  - access_token: 存在 (eyJhbGciOiJIUzI1Ni...)
  - refresh_token: 存在 (eyJhbGciOiJIUzI1Ni...)
  - user: 存在
[SSO-Callback] 从localStorage读取到token，开始验证
[SSO-Callback] Token验证成功，用户: user@example.com
```

---

## 附录

### A. 相关文档

- [AI-PPTist 用户登录 SSO 认证架构文档.md](./AI-PPTist%20用户登录%20SSO%20认证架构文档.md)
- [AI-PPTist用户登录SSO需求梳理文档.md](./AI-PPTist用户登录SSO需求梳理文档.md)
- [用户认证API接口文档.md](./用户认证API接口文档.md)

### B. 参考资料

- [SAML 2.0规范](https://docs.oasis-open.org/security/saml/v2.0/)
- [python3-saml GitHub](https://github.com/onelogin/python3-saml)
- [FastAPI安全指南](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT最佳实践](https://tools.ietf.org/html/rfc8725)
- [Vue Router导航守卫](https://router.vuejs.org/zh/guide/advanced/navigation-guards.html)

### C. 版本历史

| 版本  | 日期       | 变更内容                             |
| ----- | ---------- | ------------------------------------ |
| v1.0.0 | 2026-01-14 | 初始版本，包含完整SSO实现总结       |

---

**文档结束**
