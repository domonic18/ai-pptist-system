# AI PPTist 项目结构

本文档提供了 AI PPTist 系统的完整技术栈和文件树结构。**AI 智能体必须先阅读此文件以了解项目组织，然后再进行任何更改。**

## 技术栈

### 后端技术
- **Python 3.8+** 与 **setuptools** - 依赖管理和打包
- **FastAPI 0.104.1** - 带类型提示和异步支持的 Web 框架
- **Uvicorn 0.24.0** - 带标准扩展的 ASGI 服务器
- **Pydantic Settings 2.1.0** - 带类型验证的配置管理

### 集成服务与 API
- **OpenAI API** - AI 生成服务集成
- **腾讯云 COS SDK** - 云存储服务集成
- **PostgreSQL** - 关系型数据库
- **Redis** - 缓存和会话管理
- **MLflow 3.1.4** - AI 模型追踪和管理

### 开发与质量工具
- **Black 23.0.0+** - 代码格式化
- **Flake8 6.0.0+** - 代码质量和代码检查
- **Mypy 1.5.0+** - 静态类型检查
- **Pytest 7.4.0+** - 测试框架
- **Pre-commit 3.4.0+** - Git hooks 管理

### 前端技术
- **TypeScript** - 前端开发语言
- **Vue 3** - UI 框架
- **Vite** - 开发和构建工具
- **Element Plus** - UI 组件库
- **Pinia** - 状态管理

## 完整项目结构

```
ai-pptist-system/
├── README.md                           # 项目概览和设置
├── CLAUDE.md                           # 主 AI 上下文文件
├── backend/                            # 后端应用
│   ├── pyproject.toml                  # Python 项目配置
│   ├── app/                            # 应用代码
│   │   ├── main.py                     # FastAPI 应用入口
│   │   ├── api/                        # API 层
│   │   │   ├── v1/                     # API 版本 1
│   │   │   │   ├── router.py           # 主路由配置
│   │   │   │   ├── images.py           # 图片管理 API
│   │   │   │   ├── layout.py           # 布局优化 API
│   │   │   │   └── ai_models.py        # AI 模型管理 API
│   │   ├── models/                     # 数据模型
│   │   │   ├── ai_model.py             # AI 模型数据模型
│   │   │   ├── image.py                # 图片数据模型
│   │   │   └── base.py                 # 基础模型
│   │   ├── schemas/                    # Pydantic 模式
│   │   │   ├── ai_model.py             # AI 模型模式
│   │   │   ├── image_manager.py        # 图片管理模式
│   │   │   ├── image_search.py         # 图片搜索模式
│   │   │   └── layout_optimization.py  # 布局优化模式
│   │   ├── services/                   # 业务服务层
│   │   │   ├── ai_model/               # AI 模型服务
│   │   │   │   └── management_service.py
│   │   │   ├── image/                  # 图片服务
│   │   │   │   ├── image_generation_service.py
│   │   │   │   └── image_generation_handler.py
│   │   │   ├── layout/                 # 布局服务
│   │   │   │   ├── layout_optimization_service.py
│   │   │   │   └── layout_optimization_handler.py
│   │   │   └── repositories/           # 数据仓库
│   │   │       └── image.py            # 图片仓库
│   │   ├── prompts/                    # AI 提示词模板
│   │   │   └── presentation/           # 演示相关提示词
│   │   │       └── layout_optimization.yml
│   │   └── core/                       # 核心工具
│   │       ├── log_utils.py            # 日志工具
│   │       └── log_messages.py         # 日志消息模板
│   ├── tests/                          # 测试套件
│   │   ├── unit/                       # 单元测试
│   │   ├── integration/                # 集成测试
│   │   └── fixtures/                   # 测试夹具和数据
│   └── docker/                         # Docker 配置
│       └── database/                   # 数据库配置
│           └── init-scripts/           # 初始化脚本
├── frontend/                           # 前端应用（子模块）
│   ├── package.json                    # 前端包配置
│   ├── src/                            # 源代码
│   │   ├── components/                 # UI 组件
│   │   ├── views/                      # 页面组件
│   │   ├── stores/                     # 状态管理
│   │   ├── api/                        # API 客户端层
│   │   ├── configs/                    # 配置管理
│   │   │   └── api.ts                  # API 端点配置
│   │   └── utils/                      # 工具函数
│   └── tests/                          # 前端测试
├── docs/                               # 文档
│   ├── ai-context/                     # AI特定文档
│   │   ├── project-structure.md        # 此文件
│   │   ├── docs-overview.md            # 文档架构
│   │   ├── system-integration.md       # 集成模式
│   │   ├── deployment-infrastructure.md # 基础设施文档
│   │   └── handoff.md                  # 任务管理
│   ├── standard/                       # 开发规范
│   │   ├── API设计与实现规范.md
│   │   ├── API响应与日志规范.md
│   │   └── 前端API配置说明.md
│   ├── design/                         # 设计文档
│   │   └── frontend-interaction-design-specification.md
│   └── architecture/                   # 架构设计
├── docker/                             # Docker 配置
│   ├── docker-compose.yml              # 容器编排
│   └── database/                       # 数据库配置
└── scripts/                            # 自动化脚本
    └── setup.sh                        # 环境设置脚本
```

## 核心模块说明

### 后端架构
- **API 层**: FastAPI 路由和端点处理
- **服务层**: 业务逻辑实现
- **模型层**: SQLAlchemy 数据模型
- **模式层**: Pydantic 请求/响应验证
- **仓库层**: 数据访问抽象

### 前端架构
- **组件化**: Vue 3 组件架构
- **状态管理**: Pinia 状态管理
- **API 集成**: 统一的 API 客户端
- **配置管理**: 集中式配置管理

### 数据存储
- **PostgreSQL**: 主要业务数据存储
- **Redis**: 缓存和会话管理
- **腾讯云 COS**: 图片和文件存储

---

*此文档为 AI PPTist 系统的项目结构提供了完整概览。AI 智能体在执行任何修改前必须熟悉此结构。*