<p align="center">
    <img src='/public/logo.png' />
</p>

<p align="center">
    <a href="https://www.github.com/pipipi-pikachu/PPTist/stargazers" target="_black"><img src="https://img.shields.io/github/stars/pipipi-pikachu/PPTist?logo=github" alt="stars" /></a>
    <a href="https://www.github.com/pipipi-pikachu/PPTist/network/members" target="_black"><img src="https://img.shields.io/github/forks/pipipi-pikachu/PPTist?logo=github" alt="forks" /></a>
    <a href="https://www.github.com/pipipi-pikachu/PPTist/blob/master/LICENSE" target="_black"><img src="https://img.shields.io/github/license/pipipi-pikachu/PPTist?color=%232DCE89&logo=github" alt="license" /></a>
    <a href="https://www.typescriptlang.org" target="_black"><img src="https://img.shields.io/badge/language-TypeScript-blue.svg" alt="language"></a>
    <a href="https://github.com/pipipi-pikachu/PPTist/issues" target="_black"><img src="https://img.shields.io/github/issues-closed/pipipi-pikachu/PPTist.svg" alt="issue"></a>
    <a href="https://gitee.com/pptist/PPTist" target="_black"><img src="https://gitee.com/pptist/PPTist/badge/star.svg?version=latest" alt="gitee"></a>
</p>

简体中文 | [English](README.md)


# 🎨 AI PPTist
> PowerPoint-ist（/'pauəpɔintist/），一个基于 Web 的在线演示文稿（幻灯片）应用，还原了大部分 Office PowerPoint 常用功能，支持 文字、图片、形状、线条、图表、表格、视频、音频、公式 几种最常用的元素类型，可以在 Web 浏览器中编辑/演示幻灯片。

# ✨ 项目特色
1. **AI智能生成**：基于大语言模型智能生成PPT大纲和完整幻灯片内容
2. **易开发**：基于 Vue3.x + TypeScript 构建，不依赖UI组件库，尽量避免第三方组件，样式定制更轻松、功能扩展更方便
3. **易使用**：随处可用的右键菜单、几十种快捷键、无数次编辑细节打磨，力求还原桌面应用级体验
4. **功能丰富**：支持 PPT 中的大部分常用元素和功能，支持多种格式导出、支持移动端基础编辑和预览
5. **全栈架构**：采用前后端分离架构，前端Vue3 + 后端FastAPI，支持多模型AI服务集成

# 📥 代码拉取

## 首次克隆项目

由于本项目使用 git submodule 管理前端代码，首次克隆时需要特别注意：

### 方法一：克隆时自动初始化子模块（推荐）
```bash
git clone --recurse-submodules https://github.com/domonic18/ai-pptist-system.git
cd ai-pptist-system
```

### 方法二：先克隆主仓库，再初始化子模块
```bash
# 克隆主仓库
git clone https://github.com/domonic18/ai-pptist-system.git
cd ai-pptist-system

# 初始化并更新子模块
git submodule update --init --recursive
```

## 更新代码

### 更新主仓库代码
```bash
git pull origin master
```

### 更新子模块代码
```bash
# 更新所有子模块到最新提交
git submodule update --remote

# 或者进入子模块目录单独更新
cd frontend
git pull origin ai-pptist-frontend
```

## 子模块管理

### 查看子模块状态
```bash
git submodule status
```

### 切换子模块分支
```bash
cd frontend
git checkout ai-pptist-frontend
```

### 提交子模块更新
当子模块有更新时，需要在主仓库中提交子模块的引用：
```bash
git add frontend
git commit -m "Update frontend submodule to latest version"
```

# 🚀 快速部署运行

## 开发环境启动

### 前端启动
```bash
cd frontend
npm install
npm run dev
```
浏览器访问：http://127.0.0.1:5173/

### 后端启动
```bash
cd backend

# 安装依赖（使用pyproject.toml）
pip install -e .

# 启动后端服务
uvicorn app.main:app --reload --port 8000
```
API文档访问：http://127.0.0.1:8000/docs

## 使用部署脚本

项目提供了自动化部署脚本，用于管理生产环境和开发环境的部署：

```bash
# 启动开发环境
./scripts/deploy.sh dev up

# 停止开发环境
./scripts/deploy.sh dev down

# 重启开发环境
./scripts/deploy.sh dev restart

# 查看开发环境日志
./scripts/deploy.sh dev logs

# 查看服务状态
./scripts/deploy.sh dev status

# 构建镜像
./scripts/deploy.sh dev build

# 清理开发环境数据
./scripts/deploy.sh dev clean

# 查看脚本帮助
./scripts/deploy.sh help
```

## 配置文件说明

### 环境变量配置
项目使用统一的配置文件管理，主要配置文件位于 `config/.env`：

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/ai_pptist

# 腾讯云COS配置
COS_SECRET_ID=your_cos_secret_id
COS_SECRET_KEY=your_cos_secret_key
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name

# 应用配置
DEBUG=true
SECRET_KEY=your_secret_key
```

**注意**：大模型的API-KEY和BASE_URL配置已改为在前端页面进行配置，无需在环境变量中设置。

### 依赖管理
项目采用现代Python依赖管理最佳实践，使用`pyproject.toml`作为单一配置源：

安装依赖：
```bash
# 生产环境
pip install -e .

# 开发环境（包含测试、代码质量等工具）
pip install -e .[dev]
```


# 📚 功能列表

## AI智能生成功能
- **智能大纲生成**：基于主题自动生成PPT内容大纲
- **幻灯片内容生成**：根据大纲自动生成完整的幻灯片内容
- **多模型支持**：支持OpenAI、Azure、本地模型等多种AI服务
- **流式输出**：实时生成和预览幻灯片内容
- **模板智能匹配**：根据内容自动推荐合适的幻灯片模板

## 核心编辑功能
- **完整的幻灯片编辑器**：支持文字、图片、形状、图表、表格等元素编辑
- **多种导出格式**：支持PPTX、JSON、图片、PDF等格式导出
- **模板系统**：内置丰富的幻灯片模板
- **响应式设计**：支持移动端基础编辑和预览


# 🎯 开发

## 技术栈
- **前端**：Vue 3 + TypeScript + Vite + Pinia
- **后端**：Python FastAPI + SQLAlchemy + PostgreSQL
- **AI服务**：支持多模型（OpenAI、Azure、本地模型等）
- **存储**：PostgreSQL + 腾讯云COS

## 架构层次
```
┌─────────────────┐
│   前端层 (Vue 3)  │
├─────────────────┤
│   代理层 (Vite)   │
├─────────────────┤
│ 后端层 (FastAPI) │
├─────────────────┤
│  数据存储层       │
├─────────────────┤
│   云服务层        │
└─────────────────┘
```

## 开发文档
- [系统架构设计](docs/arch/系统架构设计.md)
- [AI PPT功能说明](docs/archive/AIPPT.md)
- [开发规范](docs/standard/README.md)


# 📄 版权声明/开源协议

## 项目来源
本项目基于原 [PPTist](https://github.com/pipipi-pikachu/PPTist) 项目开发，向原项目作者 [pipipi-pikachu](https://github.com/pipipi-pikachu) 致敬。

原项目仓库：[https://github.com/pipipi-pikachu/PPTist](https://github.com/pipipi-pikachu/PPTist)

## 开源协议
[AGPL-3.0 License](/LICENSE) | Copyright © 2020-PRESENT [pipipi-pikachu](https://github.com/pipipi-pikachu)

## 贡献说明
欢迎开发者为本项目贡献代码，共同推进AI PPT应用的发展。