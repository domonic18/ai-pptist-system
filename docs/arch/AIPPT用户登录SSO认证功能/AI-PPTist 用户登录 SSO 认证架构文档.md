# AI-PPTist 用户登录 SSO 认证架构文档

## 文档版本信息

| 版本  | 日期       | 作者         | 说明     |
| ----- | ---------- | ------------ | -------- |
| 1.0.0 | 2025-01-09 | AI Assistant | 初始版本 |

---

## 目录

1. [项目背景](#1-项目背景)
2. [参考项目分析](#2-参考项目分析)
3. [整体架构设计](#3-整体架构设计)
4. [SSO认证流程](#4-sso认证流程)
5. [数据库设计](#5-数据库设计)
6. [后端改动设计](#6-后端改动设计)
7. [前端改动设计](#7-前端改动设计)
8. [API接口设计](#8-api接口设计)
9. [安全考虑](#9-安全考虑)
10. [实施计划](#10-实施计划)

---

## 1. 项目背景

### 1.1 当前状态

**AI-PPTist** 是一个基于AI的智能PPT编辑和生成系统，采用前后端分离架构：
-**前端**: Vue 3 + TypeScript + Vite + Pinia
-**后端**: FastAPI + SQLAlchemy + PostgreSQL + Redis
-**部署**: Docker + Docker Compose
**当前认证状态**:

- 前端无登录认证
- 后端无用户认证中间件
- 数据库已有users表，但未启用认证功能

### 1.2 目标

为系统添加SSO单点登录功能，支持：

1. 账号密码登录
2. SSO单点登录
3. 登录后才能访问前端页面

### 1.3 IDP厂商信息

参考项目使用与AI-PPTist相同的IDP厂商：
| 配置项 | 值 |
|--------|-----|
| IDP Entity ID | `https://guanghua.53jy.net/idp/metadata` |
| SSO URL | `https://guanghua.53jy.net/idp/login` |
| SLO URL | `https://guanghua.53jy.net/idp/logout` |
| 协议 | SAML 2.0 |
-------------------

## 2. 参考项目分析

### 2.1 demo-flask 项目结构

```
demo-flask/
├── index.py              # 主应用文件
├── requirements.txt      # 依赖：Flask + python3-saml
├── saml/
│   ├── settings.json            # SAML基础配置
│   ├── advanced_settings.json   # SAML高级配置
│   └── certs/
│       ├── sp.key              # SP私钥
│       └── sp.crt              # SP证书
└── templates/
    ├── base.html
    ├── index.html              # 主页面（登录前/登录后）
    └── attrs.html              # 用户属性展示页面
```

### 2.2 核心认证流程

demo-flask实现了完整的SAML 2.0认证流程：

```python
# 主要路由端点
@app.route("/", methods=["GET", "POST"])
defindex():
    # 处理多种认证状态
    if"sso"in request.args:
        return redirect(auth.login())              # 发起SSO登录
    elif"acs"in request.args:
        auth.process_response()                    # 处理SAML响应
        session["samlUserdata"] = auth.get_attributes()
    elif"slo"in request.args:
        return redirect(auth.logout())             # 发起登出
    elif"sls"in request.args:
        auth.process_slo()                          # 处理登出响应
```

### 2.3 SAML配置要点

**settings.json** 关键配置：

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
    },
    "x509cert": "SP证书",
    "privateKey": "SP私钥"
  },
  "idp": {
    "entityId": "${SAML_IDP_ENTITY_ID}",
    "singleSignOnService": {
      "url": "${SAML_IDP_SSO_URL}",
    },
    "singleLogoutService": {
      "url": "${SAML_IDP_SLS_URL}",
    },
    "x509cert": "IDP证书"
  }
}
```

---

## 3. 整体架构设计

### 3.1 架构概览图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI-PPTist 系统架构                               │
└─────────────────────────────────────────────────────────────────────────────┘
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│                  │         │                  │         │                  │
│   Vue 3 前端     │         │  FastAPI 后端    │         │  SAML IDP        │
│                  │         │                  │         │  (53jy.net)      │
│  ┌────────────┐  │         │  ┌────────────┐  │         │                  │
│  │ 登录页面    │  │         │  │ SAML SP    │  │         │  ┌────────────┐  │
│  │ (账号密码)  │  │         │  │ Handler    │  │◄───────│──│ SSO Login  │  │
│  │            │  │         │  │            │  │         │  │            │  │
│  └──────┬─────┘  │         │  └──────┬─────┘  │         │  └────────────┘  │
│         │         │         │         │         │         │                  │
│         │         │         │         │         │         └──────────────────┘
│         │         │         │         │         │                  │
│         │         │         │         │         │                  │
│         │         │         │         ▼         │                  │
│         │         │         │  ┌────────────┐  │                  │
│         │         │         │  │  认证中间件 │  │                  │
│         │         │         │  │            │  │                  │
│         │         │         │  └──────┬─────┘  │                  │
│         │         │         │         │         │                  │
│         │         │         │         │         │                  │
│         │         │         │  ┌──────▼─────┐  │                  │
│         │         │         │  │ 用户管理   │  │                  │
│         │         │         │  │ Repository │  │                  │
│         │         │         │  └──────┬─────┘  │                  │
│         │         │         │         │         │                  │
│         │         │         │         │         │                  │
│         │         │         │  ┌──────▼─────┐  │                  │
│         │         │         │  │ PostgreSQL │  │                  │
│         │         │         │  │   用户表   │  │                  │
│         │         │         │  └────────────┘  │                  │
│         │         │         │                  │                  │
│  ┌──────▼─────┐  │         │  ┌────────────┐  │                  │
│  │ 主应用页面  │  │         │  │   Redis    │  │                  │
│  │ (需认证)    │◄─┼─────────┼─│ 会话存储   │  │                  │
│  └────────────┘  │         │  └────────────┘  │                  │
│                  │         │                  │                  │
└──────────────────┘         └──────────────────┘                  └──────────────────┘
```

### 3.2 技术栈选择

| 层级     | 技术          | 说明                   |
| -------- | ------------- | ---------------------- |
| 前端     | Vue 3 + Pinia | 使用Pinia管理认证状态  |
| 前端路由 | Vue Router    | 路由守卫实现认证检查   |
| 后端     | FastAPI       | 异步Python Web框架     |
| SAML库   | python3-saml  | 成熟的SAML 2.0实现     |
| 会话管理 | Redis         | 存储用户会话和JWT令牌  |
| 数据库   | PostgreSQL    | 存储用户信息和认证记录 |
| 令牌     | JWT           | 用于前后端认证通信     |

---

## 4. SSO认证流程

### 4.1 完整认证时序图

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
   │                 │ POST /auth/sso/init│                    │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │                   │ 生成SAML AuthNRequest
   │                 │                   │                    │
   │                 │                   │ ├──────────────────►│
   │                 │                   │                    │
   │                 │                   │    302 Redirect     │
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │ 302 Redirect      │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  重定向到IDP     │                   │                    │
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
   │                 │ Token + User Info │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  存储Token       │                   │                    │
   │  跳转到主页       │                   │                    │
   │◄────────────────┤                   │                    │
   │                 │                   │                    │
   │ 后续请求带Token  │                   │                    │
   ├────────────────►│                   │                    │
   │                 │                   │                    │
   │                 │ Authorization: Bearer <token>          │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │                   │ 验证Token          │
   │                 │                   │ 获取用户信息        │
   │                 │                   │                    │
   │                 │ 返回数据           │                    │
   │                 │◄──────────────────┤                    │
```

### 4.2 账号密码登录流程

```
┌───────┐         ┌─────────┐         ┌──────────┐
│ 用户  │         │ 前端    │         │ 后端     │
└───────┘         └─────────┘         └──────────┘
   │                 │                   │
   │ 访问页面         │                   │
   ├────────────────►│                   │
   │                 │                   │
   │                 │ 检查登录状态       │
   │                 ├──────────────────►│
   │                 │                   │
   │                 │ 未认证             │
   │                 │◄──────────────────┤
   │                 │                   │
   │ 重定向到登录页   │                   │
   │◄────────────────┤                   │
   │                 │                   │
   │ 输入账号密码     │                   │
   ├────────────────►│                   │
   │                 │                   │
   │                 │ POST /auth/login  │
   │                 ├──────────────────►│
   │                 │                   │
   │                 │                   │ 验证用户名密码
   │                 │                   │ 生成JWT Token
   │                 │                   │ 存储会话到Redis
   │                 │                   │
   │                 │ Token + User Info │
   │                 │◄──────────────────┤
   │                 │                   │
   │  存储Token       │                   │
   │  跳转到主页       │                   │
   │◄────────────────┤                   │
```

### 4.3 登出流程

```
┌───────┐         ┌─────────┐         ┌──────────┐         ┌─────────┐
│ 用户  │         │ 前端    │         │ 后端     │         │  IDP    │
└───────┘         └─────────┘         └──────────┘         └─────────┘
   │                 │                   │                    │
   │ 点击登出         │                   │                    │
   ├────────────────►│                   │                    │
   │                 │                   │                    │
   │                 │ POST /auth/logout │                    │
   │                 ├──────────────────►│                    │
   │                 │                   │                    │
   │                 │                   │ 清除Redis会话       │
   │                 │                   │                    │
   │                 │                   │ 如果是SSO用户        │
   │                 │                   │ 生成SAML LogoutRequest
   │                 │                   │                    │
   │                 │                   │ ├──────────────────►│
   │                 │                   │                    │
   │                 │                   │     302 Redirect    │
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │ 302 Redirect      │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  清除本地Token   │                   │                    │
   │  重定向到IDP登出 │                   │                    │
   ├─────────────────────────────────────────────────────────►│
   │                 │                   │                    │
   │                 │                   │  SAML LogoutResponse│
   │                 │                   │◄──────────────────┤
   │                 │                   │                    │
   │                 │                   │ 处理LogoutResponse  │
   │                 │                   │                    │
   │                 │ 登出成功           │                    │
   │                 │◄──────────────────┤                    │
   │                 │                   │                    │
   │  跳转到登录页     │                   │                    │
   │◄────────────────┤                   │                    │
```

---

## 5. 数据库设计

### 5.1 users表扩展

现有users表结构（来自01_schema.sql），需要添加SSO相关字段：

```sql
-- 现有字段
CREATETABLEIFNOTEXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUENOT NULL,
    nameVARCHAR(255) NOT NULL,
    passwordVARCHAR(255) NOT NULL,
    roleVARCHAR(20) NOT NULLDEFAULT'USER',
    is_active BOOLEANNOT NULLDEFAULT TRUE,
    is_superuser BOOLEANNOT NULLDEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    avatar_url VARCHAR(500),
    bio TEXT,
    preferences JSONB DEFAULT'{}'::jsonb
);
-- 需要添加的SSO相关字段
ALTERTABLE users ADD COLUMN IFNOTEXISTS auth_type VARCHAR(20) DEFAULT'password';
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_name_id VARCHAR(255);
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_session_index VARCHAR(255);
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_attributes JSONB DEFAULT'{}'::jsonb;
ALTERTABLE users ADD COLUMN IFNOTEXISTS last_sso_login_at TIMESTAMP WITH TIME ZONE;
```

### 5.2 字段说明

| 字段名             | 类型         | 说明                              | 是否必需              |
| ------------------ | ------------ | --------------------------------- | --------------------- |
| auth_type          | VARCHAR(20)  | 认证类型:`password` 或 `saml` | 否，默认 `password` |
| saml_name_id       | VARCHAR(255) | SAML NameID (用户在IDP的唯一标识) | 否                    |
| saml_session_index | VARCHAR(255) | SAML SessionIndex                 | 否                    |
| saml_attributes    | JSONB        | SAML返回的用户属性                | 否                    |
| last_sso_login_at  | TIMESTAMP    | 最后一次SSO登录时间               | 否                    |

### 5.3 索引优化

```sql
-- 为SSO相关字段添加索引
CREATEINDEXIFNOTEXISTS idx_users_auth_type ON users(auth_type);
CREATEINDEXIFNOTEXISTS idx_users_saml_name_id ON users(saml_name_id);
CREATEINDEXIFNOTEXISTS idx_users_saml_session_index ON users(saml_session_index);
```

### 5.4 用户会话表（新增）

```sql
-- 用户会话表（存储JWT会话信息）
CREATETABLEIFNOTEXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULLREFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUENOT NULL,  -- JWT ID
    refresh_token_jti VARCHAR(255) UNIQUE,   -- 刷新令牌JWT ID
    user_agent TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONENOT NULL,
    refresh_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);
-- 索引
CREATEINDEXIFNOTEXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATEINDEXIFNOTEXISTS idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATEINDEXIFNOTEXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATEINDEXIFNOTEXISTS idx_user_sessions_revoked_at ON user_sessions(revoked_at);
```

### 5.5 登录历史表（新增）

```sql
-- 登录历史表
CREATETABLEIFNOTEXISTS login_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETESETNULL,
    auth_type VARCHAR(20) NOT NULL,  -- password 或 saml
    login_status VARCHAR(20) NOT NULL,  -- success, failed
    failure_reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    saml_name_id VARCHAR(255),  -- SAML登录时记录
    created_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP
);
-- 索引
CREATEINDEXIFNOTEXISTS idx_login_history_user_id ON login_history(user_id);
CREATEINDEXIFNOTEXISTS idx_login_history_auth_type ON login_history(auth_type);
CREATEINDEXIFNOTEXISTS idx_login_history_status ON login_history(login_status);
CREATEINDEXIFNOTEXISTS idx_login_history_created_at ON login_history(created_at);
```

---

## 6. 后端改动设计

### 6.1 目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py              # 新增：认证端点
│   │       │   └── router.py            # 修改：添加auth路由
│   ├── core/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── saml_handler.py          # 新增：SAML处理器
│   │   │   ├── jwt_handler.py           # 新增：JWT处理器
│   │   │   └── password_handler.py      # 新增：密码认证处理器
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── auth.py                  # 新增：认证中间件
│   │   └── config/
│   │       ├── config.py                # 修改：添加SAML配置
│   │       └── saml_config.py           # 新增：SAML配置文件
│   ├── models/
│   │   ├── user.py                      # 新增：用户模型
│   │   ├── user_session.py              # 新增：用户会话模型
│   │   └── login_history.py             # 新增：登录历史模型
│   ├── repositories/
│   │   ├── user.py                      # 新增：用户Repository
│   │   ├── user_session.py              # 新增：会话Repository
│   │   └── login_history.py             # 新增：登录历史Repository
│   ├── schemas/
│   │   ├── auth.py                      # 新增：认证相关Schema
│   │   └── user.py                      # 新增：用户Schema
│   └── services/
│       └── auth/
│           ├── __init__.py
│           ├── auth_service.py          # 新增：认证服务
│           └── sso_service.py           # 新增：SSO服务
├── saml/                                 # 新增：SAML配置目录
│   ├── settings.json
│   ├── advanced_settings.json
│   └── certs/
│       ├── sp.key
│       └── sp.crt
└── requirements.txt                      # 修改：添加python3-saml
```

### 6.2 依赖修改

**requirements.txt** 添加：

```txt
python3-saml>=1.15.0
python-jose[cryptography]>=3.3.0  # JWT处理
passlib[bcrypt]>=1.7.4            # 密码哈希
```

### 6.3 核心代码结构

#### 6.3.1 SAML配置 (saml/settings.json)

```json
{
  "strict": true,
  "debug": false,
  "sp": {
    "entityId": "${SAML_SP_ENTITY_ID}",
    "assertionConsumerService": {
      "url": "${SAML_ACS_URL}",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    },
    "singleLogoutService": {
      "url": "${SAML_SLS_URL}",
      "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    },
    "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:transient",
    "x509cert": "${SAML_SP_CERT}",
    "privateKey": "${SAML_SP_KEY}"
  },
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

#### 6.3.2 认证端点 (app/api/v1/endpoints/auth.py)

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from app.services.auth.auth_service import AuthService
from app.schemas.auth import LoginRequest, LoginResponse, SSOInitResponse
from app.core.auth.jwt_handler import JWTHandler
from app.core.middleware.auth import get_current_user
router = APIRouter()
@router.post("/login", response_model=LoginResponse)
asyncdeflogin(
    request: LoginRequest,
    auth_service: Depends(AuthService)
):
    """账号密码登录"""
    result = await auth_service.authenticate_password(
        email=request.email,
        password=request.password
    )
    ifnot result.success:
        raise HTTPException(status_code=401, detail=result.message)
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user=result.user
    )
@router.get("/sso/init")
asyncdefinit_sso(
    request: Request,
    auth_service: Depends(AuthService)
):
    """发起SSO登录"""
    sso_url = await auth_service.init_sso_login(str(request.base_url))
    return RedirectResponse(url=sso_url)
@router.get("/sso/acs")
asyncdefsso_acs(
    request: Request,
    auth_service: Depends(AuthService)
):
    """处理SAML响应 (Assertion Consumer Service)"""
    # 处理SAML Response
    result = await auth_service.process_saml_response(request)
    ifnot result.success:
        raise HTTPException(status_code=401, detail=result.message)
    # 重定向到前端并携带token
    frontend_url = f"{result.redirect_url}#access_token={result.access_token}"
    return RedirectResponse(url=frontend_url)
@router.post("/logout")
asyncdeflogout(
    current_user = Depends(get_current_user),
    auth_service: Depends(AuthService)
):
    """登出"""
    await auth_service.logout(current_user.id)
    return {"message": "Successfully logged out"}
@router.get("/sso/slo")
asyncdefsso_slo(
    request: Request,
    auth_service: Depends(AuthService)
):
    """处理SAML登出请求/响应"""
    result = await auth_service.process_saml_logout(request)
    return RedirectResponse(url=result.redirect_url)
@router.get("/me")
asyncdefget_current_user_info(
    current_user = Depends(get_current_user)
):
    """获取当前用户信息"""
    return current_user
@router.post("/refresh")
asyncdefrefresh_token(
    refresh_token: str,
    auth_service: Depends(AuthService)
):
    """刷新访问令牌"""
    result = await auth_service.refresh_access_token(refresh_token)
    ifnot result.success:
        raise HTTPException(status_code=401, detail=result.message)
    return {"access_token": result.access_token}
```

#### 6.3.3 认证中间件 (app/core/middleware/auth.py)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth.jwt_handler import JWTHandler
from app.repositories.user import UserRepository
security = HTTPBearer()
asyncdefget_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_handler: JWTHandler = Depends(),
    user_repo: UserRepository = Depends()
):
    """获取当前认证用户"""
    token = credentials.credentials
    payload = jwt_handler.decode_token(token)
    ifnot payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    user = await user_repo.get_by_id(payload["user_id"])
    ifnot user ornot user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user
asyncdefget_current_active_user(
    current_user = Depends(get_current_user)
):
    """获取当前活跃用户"""
    ifnot current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user
```

#### 6.3.4 路由注册修改 (app/api/v1/router.py)

```python
from app.api.v1.endpoints import auth
api_router = APIRouter()
# 认证路由（无前缀，放在最前面）
api_router.include_router(auth.router, tags=["认证"])
# ... 其他路由保持不变
```

### 6.4 现有API保护

需要保护的API端点添加认证依赖：

```python
from app.core.middleware.auth import get_current_active_user
from app.api.v1.endpoints.image_manager import router as image_router
# 修改原有路由，添加认证依赖
@image_router.get("/", response_model=ImageListResponse)
asyncdeflist_images(
    current_user = Depends(get_current_active_user),  # 添加认证依赖
    page: int = 1,
    page_size: int = 20,
    image_service: ImageService = Depends()
):
    # 原有逻辑保持不变，但使用current_user.id替代硬编码的user_id
    returnawait image_service.get_user_images(
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
```

---

## 7. 前端改动设计

### 7.1 目录结构

```
frontend/src/
├── router/
│   └── index.ts                       # 修改：添加路由守卫
├── store/
│   ├── auth.ts                        # 新增：认证状态管理
│   └── index.ts                       # 修改：导出auth store
├── services/
│   ├── auth.ts                        # 新增：认证API服务
│   └── index.ts                       # 修改：导出auth服务
├── views/
│   ├── Login/                         # 新增：登录页面
│   │   ├── index.vue
│   │   └── components/
│   │       ├── LoginForm.vue          # 账号密码登录表单
│   │       └── SSOButton.vue          # SSO登录按钮
│   └── Editor/                        # 现有编辑器页面
├── composables/
│   └── useAuth.ts                     # 新增：认证组合式函数
├── types/
│   └── auth.ts                        # 新增：认证类型定义
└── utils/
    └── token.ts                       # 新增：Token工具函数
```

### 7.2 认证Store (store/auth.ts)

```typescript
import { defineStore } from'pinia'
import { ref, computed } from'vue'
importtype { User, AuthState } from'@/types/auth'
import { authService } from'@/services'
import { tokenUtils } from'@/utils/token'
exportconstuseAuthStore = defineStore('auth', () => {
  // State
  constuser = ref<User | null>(null)
  consttoken = ref<string | null>(null)
  constisAuthenticated = computed(() => !!user.value && !!token.value)
  // Actions
  asyncfunctionlogin(email: string, password: string) {
    constresult = awaitauthService.login(email, password)
    token.value = result.access_token
    user.value = result.user
    tokenUtils.setAccessToken(result.access_token)
    tokenUtils.setRefreshToken(result.refresh_token)
    returnresult
  }
  asyncfunctionssoLogin() {
    // SSO登录会重定向到IDP，不需要返回值
    window.location.href = '/api/v1/auth/sso/init'
  }
  asyncfunctionlogout() {
    awaitauthService.logout()
    user.value = null
    token.value = null
    tokenUtils.clearTokens()
  }
  asyncfunctionfetchCurrentUser() {
    try {
      constuserData = awaitauthService.getCurrentUser()
      user.value = userData
      returnuserData
    } catch (error) {
      user.value = null
      token.value = null
      tokenUtils.clearTokens()
      throwerror
    }
  }
  asyncfunctionrefreshToken() {
    constrefreshTokenValue = tokenUtils.getRefreshToken()
    if (!refreshTokenValue) {
      thrownewError('No refresh token available')
    }
    constresult = awaitauthService.refreshToken(refreshTokenValue)
    token.value = result.access_token
    tokenUtils.setAccessToken(result.access_token)
    returnresult
  }
  // 初始化：从localStorage恢复token
  functioninitialize() {
    constsavedToken = tokenUtils.getAccessToken()
    if (savedToken) {
      token.value = savedToken
      fetchCurrentUser().catch(() => {
        // Token无效，清除
        tokenUtils.clearTokens()
        token.value = null
      })
    }
  }
  return {
    user,
    token,
    isAuthenticated,
    login,
    ssoLogin,
    logout,
    fetchCurrentUser,
    refreshToken,
    initialize
  }
})
```

### 7.3 路由守卫

```typescript
import { createRouter, createWebHistory } from'vue-router'
import { useAuthStore } from'@/store'
constrouter = createRouter({
  history:createWebHistory(),
  routes: [
    {
      path:'/login',
      name:'Login',
      component: () =>import('@/views/Login/index.vue'),
      meta: { requiresAuth:false }
    },
    {
      path:'/',
      name:'Editor',
      component: () =>import('@/views/Editor/index.vue'),
      meta: { requiresAuth:true }
    }
  ]
})
// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  constauthStore = useAuthStore()
  // 如果需要认证
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      // 尝试从token恢复用户信息
      consttoken = localStorage.getItem('access_token')
      if (token) {
        try {
          awaitauthStore.fetchCurrentUser()
          next()
          return
        } catch (error) {
          // Token无效，跳转到登录页
          next({ name:'Login', query: { redirect:to.fullPath } })
          return
        }
      } else {
        // 没有token，跳转到登录页
        next({ name:'Login', query: { redirect:to.fullPath } })
        return
      }
    }
  }
  // 如果已登录且访问登录页，重定向到首页
  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name:'Editor' })
    return
  }
  next()
})
exportdefaultrouter
```

### 7.4 HTTP拦截器

修改 `services/config.ts` 添加token注入：

```typescript
importaxiosfrom'axios'
import { tokenUtils } from'@/utils/token'
constinstance = axios.create({ timeout:1000 * 300 })
// 请求拦截器：添加token
instance.interceptors.request.use(
  config=> {
    consttoken = tokenUtils.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    returnconfig
  },
  error=>Promise.reject(error)
)
// 响应拦截器：处理401错误
instance.interceptors.response.use(
  response=>response.data,
  asyncerror=> {
    constoriginalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        constauthStore = useAuthStore()
        awaitauthStore.refreshToken()
        constnewToken = tokenUtils.getAccessToken()
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        returninstance(originalRequest)
      } catch (refreshError) {
        // 刷新token失败，跳转到登录页
        constauthStore = useAuthStore()
        awaitauthStore.logout()
        window.location.href = '/login'
        returnPromise.reject(refreshError)
      }
    }
    returnPromise.reject(error)
  }
)
exportdefaultinstance
```

### 7.5 登录页面

```vue
<template>
  <divclass="login-container">
    <divclass="login-box">
      <divclass="login-header">
        <h1>AI-PPTist</h1>
        <p>智能PPT编辑和生成系统</p>
      </div>
      <el-tabsv-model="activeTab">
        <el-tab-panelabel="账号密码登录"name="password">
          <LoginForm @login="handlePasswordLogin" />
        </el-tab-pane>
        <el-tab-panelabel="SSO登录"name="sso">
          <divclass="sso-login">
            <el-button
              type="primary"
              size="large"
              @click="handleSSOLogin"
              :loading="ssoLoading"
            >
              使用企业账号登录
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>
<scriptsetuplang="ts">
import { ref } from'vue'
import { useRouter } from'vue-router'
import { useAuthStore } from'@/store'
importLoginFormfrom'./components/LoginForm.vue'
constrouter=useRouter()
constauthStore=useAuthStore()
constactiveTab=ref('password')
constssoLoading=ref(false)
asyncfunctionhandlePasswordLogin(credentials: { email:string; password:string }) {
  try {
    awaitauthStore.login(credentials.email, credentials.password)
    constredirect=router.currentRoute.value.query.redirectasstring
    router.push(redirect||'/')
  } catch (error) {
    console.error('Login failed:', error)
  }
}
functionhandleSSOLogin() {
  ssoLoading.value=true
  authStore.ssoLogin()
}
</script>
```

### 7.6 App.vue修改

添加认证初始化：

```typescript
import { onMounted } from'vue'
import { useAuthStore } from'@/store'
constauthStore = useAuthStore()
onMounted(async () => {
  // 初始化认证状态
  authStore.initialize()
  // 原有的初始化逻辑
  constslides = awaitapi.getMockData('slides')
  slidesStore.setSlides(slides)
  // ...
})
```

---

## 8. API接口设计

### 8.1 认证API端点

| 端点                      | 方法 | 描述             | 认证要求 |
| ------------------------- | ---- | ---------------- | -------- |
| `/api/v1/auth/login`    | POST | 账号密码登录     | 否       |
| `/api/v1/auth/sso/init` | GET  | 发起SSO登录      | 否       |
| `/api/v1/auth/sso/acs`  | GET  | 处理SAML响应     | 否       |
| `/api/v1/auth/sso/slo`  | GET  | 处理SAML登出     | 否       |
| `/api/v1/auth/logout`   | POST | 登出             | 是       |
| `/api/v1/auth/me`       | GET  | 获取当前用户信息 | 是       |
| `/api/v1/auth/refresh`  | POST | 刷新访问令牌     | 否       |

### 8.2 请求/响应格式

#### 8.2.1 登录请求

```typescript
// POST /api/v1/auth/login
interfaceLoginRequest {
  email: string
  password: string
}
```

#### 8.2.2 登录响应

```typescript
interfaceLoginResponse {
  access_token: string
  refresh_token: string
  token_type: 'Bearer'
  expires_in: number
  user: User
}
interfaceUser {
  id: string
  email: string
  name: string
  role: 'ADMIN' | 'USER'
  avatar_url?: string
  auth_type: 'password' | 'saml'
}
```

#### 8.2.3 SSO登录流程

```
1. 前端调用: GET /api/v1/auth/sso/init
2. 后端返回: 302 Redirect -> IDP登录页面
3. 用户在IDP完成登录
4. IDP返回: POST /api/v1/auth/sso/acs (SAML Response)
5. 后端处理SAML，生成token
6. 后端返回: 302 Redirect -> 前端应用 (带token)
```

### 8.3 标准响应格式

遵循项目的 `StandardResponse` 规范：

```typescript
interfaceStandardResponse<T> {
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

---

## 9. 安全考虑

### 9.1 密码安全

- 使用bcrypt对密码进行哈希存储 (cost factor >= 12)
- 密码最小长度要求：8个字符
- 密码复杂度要求：包含大小写字母、数字
- 登录失败限制：5次失败后锁定账户30分钟

### 9.2 Token安全

- JWT签名算法：HS256 或 RS256
- 访问令牌有效期：1小时
- 刷新令牌有效期：30天
- Token存储：HttpOnly Cookie 或 localStorage (根据需求)
- Token撤销：支持主动撤销（通过Redis黑名单）

### 9.3 SAML安全

- SAML Response签名验证
- SAML Response加密
- 时钟偏移容忍：5分钟
- Replay Attack防护：检查SAML Response的InResponseTo字段
- Audience和Recipient验证

### 9.4 传输安全

- 强制HTTPS（生产环境）
- CORS配置：仅允许可信来源
- CSP (Content Security Policy) 头部配置
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff

### 9.5 会话管理

- 会话存储：Redis（支持快速过期和撤销）
- 会话过期：与JWT token同步
- 并发会话控制：限制每个用户最多5个活跃会话
- 会话固定攻击防护：登录后重新生成会话ID

### 9.6 审计日志

- 记录所有登录/登出事件
- 记录认证失败事件（包含IP地址）
- 记录SAML认证过程
- 日志保留时间：90天

---

## 10. 实施计划

### 10.1 开发阶段

#### 阶段1：后端基础设施

1.**数据库扩展**

- 执行数据库迁移脚本，添加SSO相关字段
- 创建user_sessions和login_history表
- 添加必要的索引

2.**核心模块开发**

- JWT Handler实现
- Password Handler实现
- SAML Handler实现
- 认证中间件实现

3.**Repository和Service层**

- UserRepository扩展
- UserSessionRepository实现
- LoginHistoryRepository实现
- AuthService实现
- SSOService实现

4.**API端点开发**

- 认证端点实现
- 用户信息端点实现
- 现有API添加认证保护

#### 阶段2：前端开发

1.**认证状态管理**

- Auth Store实现
- Token工具函数
- 认证组合式函数

2.**路由和导航**

- 路由守卫实现
- 登录页面开发
- 登录流程集成

3.**HTTP拦截器**

- Token注入
- 自动token刷新
- 401错误处理

4.**UI组件**

- 登录表单组件
- SSO登录按钮
- 用户信息展示

#### 阶段3：测试和调试 

1.**单元测试**

- 认证服务测试
- JWT Handler测试
- SAML Handler测试

2.**集成测试**

- 登录流程测试
- SSO流程测试
- Token刷新测试
- API保护测试

3.**端到端测试**

- 完整登录流程
- 登出流程
- 会话过期处理

4.**SSO联调测试**

- 与IDP联调
- SAML配置验证
- 用户属性映射验证

#### 阶段4：部署和上线 

1.**环境配置**

- SAML证书生成
- IDP配置更新
- 环境变量配置
- Docker Compose配置更新

2.**数据迁移**

- 现有用户数据迁移
- 生产数据库更新

3.**上线部署**

- 蓝绿部署
- 灰度发布（可选）

4.**监控和验证**

- 监控认证成功率
- 监控SSO认证性能
- 收集用户反馈

### 10.2 关键里程碑

| 里程碑       | 预计完成时间 | 交付物                    |
| ------------ | ------------ | ------------------------- |
| M1: 后端基础 |              | 认证API、JWT/SAML Handler |
| M2: 前端基础 |              | 登录页面、认证状态管理    |
| M3: 集成测试 |              | 完整的登录/登出流程       |
| M4: SSO联调  |              | SAML认证集成完成          |
| M5: 生产部署 |              | 系统上线                  |

### 10.3 风险和缓解措施

| 风险             | 影响 | 缓解措施                              |
| ---------------- | ---- | ------------------------------------- |
| IDP配置问题      | 高   | 提前与IDP提供商沟通，获取完整配置文档 |
| SAML证书过期     | 中   | 设置证书过期监控，提前准备更新流程    |
| 现有用户数据迁移 | 中   | 充分测试迁移脚本，准备回滚方案        |
| 性能影响         | 低   | 使用Redis缓存，优化SAML验证流程       |
| 前端兼容性问题   | 低   | 充分测试主流浏览器，准备降级方案      |

---

## 附录

### A. 参考文档

- [SAML 2.0规范](https://docs.oasis-open.org/security/saml/v2.0/)
- [python3-saml文档](https://github.com/onelogin/python3-saml)
- [FastAPI安全指南](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT最佳实践](https://tools.ietf.org/html/rfc8725)

### B. 环境变量配置

```bash
# SAML配置
SAML_SP_ENTITY_ID=http://localhost:8000/api/v1/auth/metadata
SAML_ACS_URL=http://localhost:8000/api/v1/auth/sso/acs
SAML_SLS_URL=http://localhost:8000/api/v1/auth/sso/slo
SAML_SP_CERT=<SP证书内容>
SAML_SP_KEY=<SP私钥内容>
SAML_IDP_ENTITY_ID=<IDP实体ID>
SAML_IDP_SSO_URL=<IDP单点登录URL>
SAML_IDP_SLS_URL=<IDP单点登出URL>
SAML_IDP_CERT=<IDP证书内容>
# JWT配置
SECRET_KEY=<JWT密钥>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
# CORS配置
FRONTEND_URL=http://localhost:3005
```

### C. 数据库迁移脚本

```sql
-- 09_sso_support.sql
-- 添加SSO支持
-- 1. 扩展users表
ALTERTABLE users ADD COLUMN IFNOTEXISTS auth_type VARCHAR(20) DEFAULT'password';
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_name_id VARCHAR(255);
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_session_index VARCHAR(255);
ALTERTABLE users ADD COLUMN IFNOTEXISTS saml_attributes JSONB DEFAULT'{}'::jsonb;
ALTERTABLE users ADD COLUMN IFNOTEXISTS last_sso_login_at TIMESTAMP WITH TIME ZONE;
-- 2. 添加索引
CREATEINDEXIFNOTEXISTS idx_users_auth_type ON users(auth_type);
CREATEINDEXIFNOTEXISTS idx_users_saml_name_id ON users(saml_name_id);
CREATEINDEXIFNOTEXISTS idx_users_saml_session_index ON users(saml_session_index);
-- 3. 创建用户会话表
CREATETABLEIFNOTEXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULLREFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUENOT NULL,
    refresh_token_jti VARCHAR(255) UNIQUE,
    user_agent TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONENOT NULL,
    refresh_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);
CREATEINDEXIFNOTEXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATEINDEXIFNOTEXISTS idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATEINDEXIFNOTEXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
-- 4. 创建登录历史表
CREATETABLEIFNOTEXISTS login_history (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETESETNULL,
    auth_type VARCHAR(20) NOT NULL,
    login_status VARCHAR(20) NOT NULL,
    failure_reason VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    saml_name_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONENOT NULLDEFAULT CURRENT_TIMESTAMP
);
CREATEINDEXIFNOTEXISTS idx_login_history_user_id ON login_history(user_id);
CREATEINDEXIFNOTEXISTS idx_login_history_auth_type ON login_history(auth_type);
CREATEINDEXIFNOTEXISTS idx_login_history_status ON login_history(login_status);
CREATEINDEXIFNOTEXISTS idx_login_history_created_at ON login_history(created_at);
-- 5. 创建更新时间触发器
DO $$
BEGIN
    IFNOTEXISTS (SELECT1FROM pg_trigger WHERE tgname = 'trigger_user_sessions_updated_at') THEN
        CREATETRIGGERtrigger_user_sessions_updated_at
            BEFOREUPDATEON user_sessions
            FOR EACH ROW
            EXECUTEFUNCTION update_updated_at_column();
    ENDIF;
END $$;
```

---

**文档结束**
