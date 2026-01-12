# AI-PPTist 用户认证系统需求梳理文档

## 文档信息

| 项目     | 内容                           |
| -------- | ------------------------------ |
| 文档名称 | AI-PPTist 用户认证系统需求梳理 |
| 文档版本 | v1.0.0                         |
| 创建日期 | 2025-01-09                     |
| 项目名称 | AI-PPTist                      |
| 文档状态 | 草稿                           |

---

## 目录

1. [项目背景](#1-项目背景)
2. [当前状态分析](#2-当前状态分析)
3. [需求概述](#3-需求概述)
4. [功能需求](#4-功能需求)
5. [非功能需求](#5-非功能需求)
6. [技术需求](#6-技术需求)
7. [参考配置](#7-参考配置)
8. [实施建议](#8-实施建议)

---

## 1. 项目背景

### 1.1 项目简介

AI-PPTist 是一个基于AI的智能PPT编辑和生成系统，采用前后端分离架构：

- **前端**: Vue 3 + TypeScript + Vite + Pinia
- **后端**: FastAPI + SQLAlchemy + PostgreSQL + Redis
- **部署**: Docker + Docker Compose

### 1.2 需求来源

当前系统**没有实现任何用户认证功能**，所有用户可以直接访问系统，存在以下问题：

1. **数据安全隐患**：用户数据无法隔离，任何人都可以访问所有数据
2. **无法追溯操作**：无法记录是谁创建了哪些PPT、上传了哪些图片
3. **缺乏权限控制**：无法实现不同用户的权限管理
4. **不符合企业规范**：企业内部系统需要统一的身份认证

### 1.3 解决方案

为AI-PPTist系统添加完整的用户认证功能，支持：

- 账号密码登录
- 用户注册
- SSO单点登录（基于SAML 2.0协议）

---

## 2. 当前状态分析

### 2.1 现有代码分析

#### 2.1.1 前端状态

**文件位置**: `C:\projects\ai-ppt\ai-pptist-system\frontend`

**当前情况**:

- ✅ 已有Vue 3 + TypeScript项目结构
- ✅ 使用Pinia进行状态管理 (`frontend/src/store/`)
- ❌ 无用户认证相关代码
- ❌ 无登录页面
- ❌ 无路由守卫
- ❌ 无认证状态管理

**关键文件**:

- `frontend/src/main.ts` - 应用入口，无认证初始化
- `frontend/src/App.vue` - 根组件，直接加载编辑器
- `frontend/src/store/index.ts` - 状态管理，无auth store
- `frontend/src/services/index.ts` - API服务，无认证相关API

#### 2.1.2 后端状态

**文件位置**: `C:\projects\ai-ppt\ai-pptist-system\backend`

**当前情况**:

- ✅ 已有FastAPI项目结构
- ✅ 已有users表（数据库Schema）
- ✅ 已有数据库模型和Repository
- ❌ 无认证中间件
- ❌ 无JWT Token处理
- ❌ 无SAML SSO实现
- ❌ 无密码加密验证
- ❌ API端点无保护

**关键文件**:

- `backend/main.py` - 应用入口，无认证中间件
- `backend/app/api/v1/router.py` - 路由聚合，无auth端点
- `backend/app/core/config/config.py` - 配置管理，有安全配置字段但未使用
- `backend/app/db/database.py` - 数据库配置，支持异步会话

#### 2.1.3 数据库状态

**表结构** (来自 `docker/database/init-scripts/01_schema.sql`):

```sql
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    avatar_url VARCHAR(500),
    bio TEXT,
    preferences JSONB DEFAULT '{}'::jsonb
);
```

**当前状态**:

- ✅ users表已存在
- ❌ 缺少SSO相关字段（saml_name_id, auth_type等）
- ❌ 缺少会话管理表（user_sessions）
- ❌ 缺少登录历史表（login_history）

### 2.2 参考Demo分析

**文件位置**: `C:\projects\ai-ppt\ai-pptist-system\demo-flask`

**项目结构**:

```
demo-flask/
├── index.py                    # Flask主应用
├── requirements.txt            # Flask + python3-saml
├── saml/
│   ├── settings.json           # SAML配置
│   ├── advanced_settings.json  # 高级配置
│   └── certs/
│       ├── sp.key             # SP私钥
│       └── sp.crt             # SP证书
└── templates/
    ├── index.html             # 主页面
    └── attrs.html             # 用户属性页面
```

**核心实现**:

- 使用 `python3-saml` 库实现SAML 2.0认证
- 已配置好SP（Service Provider）和IDP（Identity Provider）
- SSO流程已验证可用

---

## 3. 需求概述

### 3.1 核心目标

为AI-PPTist系统添加完整的用户认证功能，确保：

1. **用户必须登录才能使用系统**
2. **支持两种登录方式**：账号密码登录、SSO单点登录
3. **支持用户注册功能**
4. **前后端都需要进行认证检查**

### 3.2 需求优先级

| 优先级 | 功能         | 说明                   |
| ------ | ------------ | ---------------------- |
| P0     | 账号密码登录 | 基础功能，必须实现     |
| P0     | 前端路由守卫 | 未登录用户无法访问系统 |
| P0     | 后端API保护  | 未认证用户无法访问数据 |
| P0     | 用户注册     | 新用户注册功能         |
| P1     | SSO单点登录  | 企业统一认证集成       |
| P1     | 用户信息管理 | 查看和编辑个人信息     |
| P2     | 登录历史记录 | 审计和追溯             |
| P2     | 会话管理     | 多设备登录控制         |

### 3.3 范围界定

**包含范围**:

- ✅ 用户注册
- ✅ 账号密码登录
- ✅ SSO单点登录
- ✅ 登出功能
- ✅ Token刷新机制
- ✅ 路由守卫和API保护
- ✅ 用户信息获取

**不包含范围**:

- ❌ 密码找回功能（后续版本）
- ❌ 第三方社交登录（如微信、GitHub）
- ❌ 多因素认证（MFA）
- ❌ 用户权限细分（当前只有ADMIN和USER两种角色）

---

## 4. 功能需求

### 4.1 用户注册 (FR-001)

**需求描述**: 新用户可以通过注册功能创建账户

**功能点**:

1. **注册表单**

   - 邮箱地址（必填，唯一性验证）
   - 用户名（必填，2-50个字符）
   - 密码（必填，8个字符以上，包含大小写字母和数字）
   - 确认密码（必填，需与密码一致）
2. **验证规则**

   - 邮箱格式验证
   - 邮箱是否已注册检查
   - 用户名长度和格式验证
   - 密码强度验证
   - 两次密码输入一致性验证
3. **注册流程**

   ```
   用户填写注册表单
   → 前端验证
   → 提交到后端
   → 后端二次验证
   → 密码加密（bcrypt）
   → 创建用户记录
   → 返回注册成功
   → 自动登录或跳转到登录页
   ```
4. **错误处理**

   - 邮箱已存在：提示"该邮箱已被注册"
   - 网络错误：提示"注册失败，请稍后重试"
   - 服务器错误：提示"服务器错误，请联系管理员"

**验收标准**:

- [ ] 用户可以使用有效邮箱成功注册
- [ ] 重复邮箱注册时显示正确错误提示
- [ ] 密码不符合要求时显示具体要求
- [ ] 注册成功后自动登录或跳转到登录页

---

### 4.2 账号密码登录 (FR-002)

**需求描述**: 已注册用户可以使用邮箱和密码登录系统

**功能点**:

1. **登录表单**

   - 邮箱地址（必填）
   - 密码（必填）
   - 记住我（可选）
   - 忘记密码（链接，暂不实现）
2. **验证规则**

   - 邮箱格式验证
   - 密码非空验证
3. **登录流程**

   ```
   用户输入邮箱密码
   → 点击登录按钮
   → 前端验证
   → 发送登录请求到后端
   → 后端验证邮箱和密码
   → 生成JWT Token（access_token + refresh_token）
   → 返回Token和用户信息
   → 前端存储Token
   → 跳转到主页
   ```
4. **错误处理**

   - 邮箱或密码错误：提示"邮箱或密码错误"
   - 账户被禁用：提示"账户已被禁用，请联系管理员"
   - 网络错误：提示"登录失败，请检查网络连接"

**验收标准**:

- [ ] 使用正确的邮箱和密码可以成功登录
- [ ] 使用错误的邮箱或密码显示错误提示
- [ ] 登录成功后正确跳转到主页
- [ ] Token正确存储在本地

---

### 4.3 SSO单点登录 (FR-003)

**需求描述**: 用户可以通过企业SSO系统登录

**功能点**:

1. **SSO登录入口**

   - 登录页面提供SSO登录按钮
   - 按钮文案："使用企业账号登录"
2. **SSO登录流程**

   ```
   用户点击SSO登录按钮
   → 前端调用 /api/v1/auth/sso/init
   → 后端生成SAML AuthNRequest
   → 重定向到IDP登录页面
   → 用户在IDP输入企业账号密码
   → IDP验证成功
   → IDP发送SAML Response到ACS端点
   → 后端验证SAML Response
   → 提取用户信息
   → 创建或更新用户记录
   → 生成JWT Token
   → 重定向回前端（携带Token）
   → 前端存储Token
   → 跳转到主页
   ```
3. **用户信息映射**

   | SAML属性         | 用户字段        | 说明                |
   | ---------------- | --------------- | ------------------- |
   | NameID           | saml_name_id    | 用户在IDP的唯一标识 |
   | Email            | email           | 用户邮箱            |
   | DisplayName/Name | name            | 用户显示名称        |
   | 其他属性         | saml_attributes | 存储在JSONB字段     |
4. **首次SSO登录**

   - 自动创建用户记录
   - auth_type设置为"saml"
   - 如果邮箱与现有账号冲突，需要特殊处理

**验收标准**:

- [ ] 点击SSO登录按钮能正确跳转到IDP
- [ ] 在IDP登录后能正确返回到系统
- [ ] 首次SSO登录能自动创建用户
- [ ] SSO登录用户能正常访问系统功能

---

### 4.4 用户登出 (FR-004)

**需求描述**: 登录用户可以主动登出系统

**功能点**:

1. **登出方式**

   - 前端登出按钮（通常在用户菜单中）
   - API调用：`POST /api/v1/auth/logout`
2. **登出流程**

   ```
   用户点击登出按钮
   → 调用后端登出API
   → 后端清除会话（Redis）
   → 记录登出历史
   → 返回登出成功
   → 前端清除本地Token
   → 清除认证状态
   → 跳转到登录页
   ```
3. **SSO用户登出**

   - 除了本地登出，还需要调用IDP的登出端点
   - 实现Single Logout (SLO)

**验收标准**:

- [ ] 点击登出按钮能成功登出
- [ ] 登出后无法访问需要认证的页面
- [ ] 登出后Token被清除
- [ ] SSO用户登出后需要重新在IDP登录

---

### 4.5 Token刷新 (FR-005)

**需求描述**: 当访问令牌过期时，自动使用刷新令牌获取新的访问令牌

**功能点**:

1. **Token类型**

   - Access Token：短期有效（1小时），用于API调用
   - Refresh Token：长期有效（30天），用于刷新Access Token
2. **刷新时机**

   - API返回401错误时
   - Access Token即将过期前（提前5分钟）
3. **刷新流程**

   ```
   API请求返回401
   → 拦截器捕获错误
   → 使用refresh_token调用刷新接口
   → 后端验证refresh_token
   → 生成新的access_token
   → 返回新的access_token
   → 重试原请求
   ```
4. **刷新失败处理**

   - Refresh Token过期或无效
   - 清除本地Token
   - 跳转到登录页

**验收标准**:

- [ ] Token过期时能自动刷新
- [ ] 刷新成功后用户无感知
- [ ] 刷新失败后正确跳转到登录页

---

### 4.6 前端路由守卫 (FR-006)

**需求描述**: 未登录用户访问需要认证的页面时，自动跳转到登录页

**功能点**:

1. **路由配置**

   - 登录页：`/login`（无需认证）
   - 主页/编辑器：`/`（需要认证）
2. **路由守卫逻辑**

   ```typescript
   router.beforeEach((to, from, next) => {
     if (to.meta.requiresAuth) {
       if (!isAuthenticated) {
         // 尝试从token恢复用户信息
         if (hasToken) {
           fetchCurrentUser().then(() => next())
         } else {
           next({ path: '/login', query: { redirect: to.fullPath } })
         }
       } else {
         next()
       }
     } else {
       next()
     }
   })
   ```
3. **登录后跳转**

   - 登录成功后跳转到原始访问页面
   - 如果没有原始页面，跳转到主页

**验收标准**:

- [ ] 未登录访问主页自动跳转到登录页
- [ ] 登录成功后跳转到原始访问页面
- [ ] 已登录用户访问登录页自动跳转到主页
- [ ] 登出后无法访问需要认证的页面

---

### 4.7 后端API保护 (FR-007)

**需求描述**: 所有后端API都需要验证用户登录状态

**功能点**:

1. **认证中间件**

   - 验证JWT Token
   - 提取用户信息
   - 检查用户状态（是否被禁用）
2. **保护范围**

   - 所有业务API端点
   - 除了认证相关端点（/api/v1/auth/*）
3. **实现方式**

   ```python
   @router.get("/")
   async def list_images(
       current_user = Depends(get_current_user),  # 认证依赖
       page: int = 1,
       page_size: int = 20
   ):
       # 使用current_user.id进行数据过滤
       return await image_service.get_user_images(
           user_id=current_user.id,
           page=page,
           page_size=page_size
       )
   ```
4. **错误响应**

   - 401 Unauthorized：Token无效或过期
   - 403 Forbidden：用户无权限或账户被禁用

**验收标准**:

- [ ] 未认证用户访问API返回401错误
- [ ] 已认证用户可以正常访问API
- [ ] Token过期后返回401错误
- [ ] 被禁用用户访问API返回403错误

---

### 4.8 用户信息获取 (FR-008)

**需求描述**: 前端可以获取当前登录用户的信息

**功能点**:

1. **API端点**

   - `GET /api/v1/auth/me`：获取当前用户信息
2. **返回信息**

   ```json
   {
     "id": "user_001",
     "email": "user@example.com",
     "name": "张三",
     "role": "USER",
     "avatar_url": null,
     "auth_type": "password",
     "created_at": "2025-01-01T00:00:00Z",
     "last_login_at": "2025-01-09T10:30:00Z"
   }
   ```
3. **使用场景**

   - 页面显示用户名和头像
   - 判断用户角色显示不同功能
   - 判断认证类型（显示"账号密码登录"或"SSO登录"）

**验收标准**:

- [ ] API正确返回当前用户信息
- [ ] 信息包含所有必要字段
- [ ] 未认证用户调用返回401错误

---

### 4.9 数据隔离 (FR-009)

**需求描述**: 用户只能访问自己的数据

**功能点**:

1. **数据隔离范围**

   - 图片上传（images表）
   - PPT演示文稿（presentations表）
   - 幻灯片（slides表）
   - 生成任务（banana_generation_tasks表）
2. **实现方式**

   - 在Repository层强制加入user_id过滤
   - API层使用current_user.id传入
3. **示例**

   ```python
   # 修改前：所有用户可以看到所有图片
   async def get_images(page: int = 1, page_size: int = 20):
       return await db.query(Image).offset(...).limit(...)

   # 修改后：只能看到自己的图片
   async def get_images(user_id: str, page: int = 1, page_size: int = 20):
       return await db.query(Image).filter(
           Image.user_id == user_id
       ).offset(...).limit(...)
   ```

**验收标准**:

- [ ] 用户只能看到自己上传的图片
- [ ] 用户只能看到自己创建的PPT
- [ ] 用户A无法访问用户B的数据

---

## 5. 非功能需求

### 5.1 安全性需求 (NFR-001)

| 需求项      | 说明                                  | 优先级 |
| ----------- | ------------------------------------- | ------ |
| 密码加密    | 使用bcrypt加密存储，cost factor >= 12 | P0     |
| Token签名   | JWT使用HS256或RS256签名               | P0     |
| HTTPS传输   | 生产环境强制使用HTTPS                 | P0     |
| SQL注入防护 | 使用ORM和参数化查询                   | P0     |
| XSS防护     | 前端对用户输入进行转义                | P0     |
| CSRF防护    | 实现CSRF Token验证                    | P1     |
| 登录限流    | 5次失败后锁定30分钟                   | P1     |
| 会话超时    | Access Token 1小时过期                | P0     |
| 审计日志    | 记录所有登录/登出事件                 | P2     |

### 5.2 性能需求 (NFR-002)

| 指标          | 目标值  | 说明             |
| ------------- | ------- | ---------------- |
| 登录响应时间  | < 500ms | 账号密码登录     |
| SSO登录时间   | < 3s    | 从点击到完成认证 |
| Token验证时间 | < 50ms  | 每次API请求      |
| 并发登录支持  | 100 QPS | 高峰期登录请求   |

### 5.3 可用性需求 (NFR-003)

| 需求项     | 说明                             |
| ---------- | -------------------------------- |
| 错误提示   | 用户友好的错误提示，避免技术术语 |
| 加载状态   | 登录按钮显示loading状态          |
| 密码可见性 | 提供密码显示/隐藏切换            |
| 记住我功能 | 可选记住登录状态（30天）         |
| 快捷登录   | SSO登录一键完成                  |

### 5.4 兼容性需求 (NFR-004)

| 平台   | 支持情况                                      |
| ------ | --------------------------------------------- |
| 浏览器 | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| 设备   | PC端优先，移动端兼容                          |
| 屏幕   | 最小支持 1024x768                             |

---

## 6. 技术需求

### 6.1 前端技术栈

```json
{
  "框架": "Vue 3.4+",
  "语言": "TypeScript 5.0+",
  "构建工具": "Vite 5.0+",
  "状态管理": "Pinia 2.1+",
  "路由": "Vue Router 4.2+",
  "UI组件": "Element Plus",
  "HTTP客户端": "Axios",
  "Token存储": "localStorage / sessionStorage"
}
```

**需要新增的依赖**:

```json
{
  "devDependencies": {
    // 无需额外依赖，使用现有技术栈
  }
}
```

### 6.2 后端技术栈

```json
{
  "框架": "FastAPI 0.104+",
  "语言": "Python 3.10+",
  "数据库": "PostgreSQL 15",
  "缓存": "Redis 7",
  "ORM": "SQLAlchemy 2.0+",
  "SAML库": "python3-saml 1.15.0+",
  "JWT库": "python-jose[cryptography]",
  "密码库": "passlib[bcrypt]"
}
```

**需要新增的依赖** (`requirements.txt`):

```txt
python3-saml>=1.15.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### 6.3 数据库需求

**表结构变更**:

1. **users表扩展**

```sql
-- 新增字段
ALTER TABLE users ADD COLUMN auth_type VARCHAR(20) DEFAULT 'password';
ALTER TABLE users ADD COLUMN saml_name_id VARCHAR(255);
ALTER TABLE users ADD COLUMN saml_session_index VARCHAR(255);
ALTER TABLE users ADD COLUMN saml_attributes JSONB DEFAULT '{}'::jsonb;
ALTER TABLE users ADD COLUMN last_sso_login_at TIMESTAMP WITH TIME ZONE;

-- 新增索引
CREATE INDEX idx_users_auth_type ON users(auth_type);
CREATE INDEX idx_users_saml_name_id ON users(saml_name_id);
```

2. **user_sessions表（新建）**

```sql
CREATE TABLE user_sessions (
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
```

3. **login_history表（新建）**

```sql
CREATE TABLE login_history (
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
```

### 6.4 接口规范

**请求格式**:

```typescript
// Content-Type: application/json
{
  "field1": "value1",
  "field2": "value2"
}
```

**响应格式**（遵循项目规范）:

```typescript
interface StandardResponse<T> {
  status: 'success' | 'error'
  data?: T
  error?: {
    code: string
    message: string
    details?: any
  }
  timestamp: string
  request_id: string
}
```

**认证头部**:

```
Authorization: Bearer <access_token>
```

---

## 7. 参考配置

### 7.1 SAML配置复用

从demo-flask项目复用以下配置：

#### 7.1.1 SP配置（需要调整）

**原配置** (demo-flask):

```json
{
  "sp": {
    "entityId": "http://localhost:8000/metadata/",
    "assertionConsumerService": {
      "url": "http://localhost:8000/?acs",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    },
    "singleLogoutService": {
      "url": "http://localhost:8000/?sls",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    }
  }
}
```

**需要调整为** (AI-PPTist):

```json
{
  "sp": {
    "entityId": "http://localhost:8080/api/v1/auth/metadata",
    "assertionConsumerService": {
      "url": "http://localhost:8080/api/v1/auth/sso/acs",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    },
    "singleLogoutService": {
      "url": "http://localhost:8080/api/v1/auth/sso/slo",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    }
  }
}
```

**调整说明**:

- 端口从8000改为8080（与AI-PPTist后端端口一致）
- 路径添加了 `/api/v1/auth`前缀
- metadata端点改为 `/api/v1/auth/metadata`

#### 7.1.2 IDP配置（直接复用）

```json
{
  "idp": {
    "entityId": "${SAML_IDP_ENTITY_ID}",
    "singleSignOnService": {
      "url": "${SAML_IDP_SSO_URL}",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "singleLogoutService": {
      "url": "${SAML_IDP_SLS_URL}",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "x509cert": "${SAML_IDP_CERT}"
  }
}
```

#### 7.1.3 证书配置（直接复用）

**SP证书和私钥**（从demo-flask/saml/certs/复制）:

- `sp.key` - SP私钥
- `sp.crt` - SP证书

### 7.2 环境变量配置

**需要在 `config/.env` 中添加**:

```bash
# ==================== SAML配置 ====================
SAML_SP_ENTITY_ID=http://localhost:8080/api/v1/auth/metadata
SAML_ACS_URL=http://localhost:8080/api/v1/auth/sso/acs
SAML_SLS_URL=http://localhost:8080/api/v1/auth/sso/slo
SAML_IDP_ENTITY_ID=IDP实体ID
SAML_IDP_SSO_URL=IDP单点登录URL
SAML_IDP_SLS_URL=IDP单点登出URL


# SAML证书（直接使用demo-flask的证书）
SAML_SP_CERT=$(cat saml/certs/sp.crt | sed 's/-----BEGIN CERTIFICATE-----//g' | sed 's/-----END CERTIFICATE-----//g' | tr -d '\n')
SAML_SP_KEY=$(cat saml/certs/sp.key | sed 's/-----BEGIN PRIVATE KEY-----//g' | sed 's/-----END PRIVATE KEY-----//g' | tr -d '\n')

# IDP证书
SAML_IDP_CERT="MIIDjjCCAnYCCQC+wM+JDlHORjANBgkqhkiG9w0..."

# ==================== JWT配置 ====================
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# ==================== 密码配置 ====================
PASSWORD_BCRYPT_ROUNDS=12
```

---

## 8. 实施建议

### 8.1 开发顺序建议

**阶段1：基础认证功能（P0）**

1. 数据库表扩展和迁移
2. 后端认证基础设施（JWT、密码处理）
3. 用户注册API
4. 账号密码登录API
5. 前端登录页面
6. 前端路由守卫
7. 后端API保护

**阶段2：SSO集成（P1）**

1. SAML配置文件准备
2. 后端SAML Handler实现
3. SSO登录API
4. 前端SSO登录按钮
5. SSO流程联调测试

**阶段3：增强功能（P2）**

1. Token刷新机制
2. 登出功能完善
3. 登录历史记录
4. 会话管理
5. 用户信息页面

### 8.2 测试建议

**单元测试**:

- [ ] 密码加密和验证
- [ ] JWT Token生成和验证
- [ ] SAML请求生成和响应解析
- [ ] 用户注册逻辑
- [ ] 登录逻辑

**集成测试**:

- [ ] 完整登录流程（账号密码）
- [ ] 完整登录流程（SSO）
- [ ] Token刷新流程
- [ ] 登出流程
- [ ] API访问控制

**端到端测试**:

- [ ] 用户注册到登录的完整流程
- [ ] SSO登录到访问系统的完整流程
- [ ] Token过期后的自动刷新
- [ ] 多设备登录和登出

**SSO联调测试**:

- [ ] 与IDP提供商联调
- [ ] SAML Request验证
- [ ] SAML Response验证
- [ ] 用户属性映射
- [ ] Single Logout测试

### 8.3 风险提示

| 风险项      | 风险等级 | 缓解措施                       |
| ----------- | -------- | ------------------------------ |
| IDP配置变更 | 中       | 提前与IDP提供商确认配置稳定性  |
| 证书过期    | 中       | 设置证书过期监控，提前准备更新 |
| 用户冲突    | 低       | SSO登录时邮箱冲突的处理策略    |
| 性能影响    | 低       | 使用Redis缓存会话信息          |
| 兼容性问题  | 低       | 充分测试主流浏览器             |

### 8.4 后续优化建议

**短期优化**（上线后1-2个月）:

1. 添加密码找回功能
2. 添加邮箱验证功能
3. 优化登录页面UI/UX
4. 添加登录历史查看
5. 实现多设备管理

**长期优化**（上线后3-6个月）:

1. 添加多因素认证（MFA）
2. 添加第三方社交登录
3. 实现细粒度权限控制
4. 添加用户组功能
5. 实现单点登出（SLO）全局控制

---

## 附录

### A. API端点清单

| 端点                      | 方法 | 描述             | 认证要求 |
| ------------------------- | ---- | ---------------- | -------- |
| `/api/v1/auth/register` | POST | 用户注册         | 否       |
| `/api/v1/auth/login`    | POST | 账号密码登录     | 否       |
| `/api/v1/auth/sso/init` | GET  | 发起SSO登录      | 否       |
| `/api/v1/auth/sso/acs`  | POST | 处理SAML响应     | 否       |
| `/api/v1/auth/sso/slo`  | GET  | 处理SAML登出     | 否       |
| `/api/v1/auth/logout`   | POST | 登出             | 是       |
| `/api/v1/auth/me`       | GET  | 获取当前用户信息 | 是       |
| `/api/v1/auth/refresh`  | POST | 刷新访问令牌     | 否       |
| `/api/v1/auth/metadata` | GET  | SP元数据         | 否       |

### B. 数据字段映射

**用户信息映射**:

| 字段名        | 类型         | 说明         | 示例                   |
| ------------- | ------------ | ------------ | ---------------------- |
| id            | VARCHAR(36)  | 用户唯一标识 | "user_001"             |
| email         | VARCHAR(255) | 用户邮箱     | "user@example.com"     |
| name          | VARCHAR(255) | 用户显示名称 | "张三"                 |
| password      | VARCHAR(255) | 密码哈希     | bcrypt哈希             |
| role          | VARCHAR(20)  | 用户角色     | "USER" / "ADMIN"       |
| auth_type     | VARCHAR(20)  | 认证类型     | "password" / "saml"    |
| saml_name_id  | VARCHAR(255) | SAML NameID  | "user@saml.idp"        |
| is_active     | BOOLEAN      | 是否激活     | true                   |
| created_at    | TIMESTAMP    | 创建时间     | "2025-01-09T10:00:00Z" |
| last_login_at | TIMESTAMP    | 最后登录时间 | "2025-01-09T10:30:00Z" |

### C. 参考文档

- [python3-saml GitHub](https://github.com/onelogin/python3-saml)
- [SAML 2.0规范](https://docs.oasis-open.org/security/saml/v2.0/)
- [FastAPI安全指南](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT最佳实践](https://tools.ietf.org/html/rfc8725)
- [Vue Router导航守卫](https://router.vuejs.org/zh/guide/advanced/navigation-guards.html)

### D. 联系方式

如有疑问，请联系：

- 项目负责人：[待填写]
- 技术支持：[待填写]
- IDP提供商：[待填写]

---

**文档结束**