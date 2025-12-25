# 🎨 AI PPTist
> PowerPoint-ist（/'pauəpɔintist/），一个基于 Web 的智能演示文稿应用。通过集成先进的文生图模型，自动生成精美的PPT内容，支持在 Web 浏览器中编辑和演示幻灯片。

# ✨ 项目特色
1. **AI智能生成**：基于大语言模型智能生成PPT大纲和完整幻灯片内容
2. **智能规划内容**：基于大模型自动分析大纲结构并批量生成高质量幻灯片，大幅提升创作效率
3. **文生图驱动**：基于`Nano Banana Pro`的文生图能力，根据内容自动生成精美PPT，大幅提升创作效率
4. **功能丰富**：支持 `PPT` 中的大部分常用元素和功能，支持多种格式导出、支持移动端基础编辑和预览
5. **全栈架构**：采用前后端分离架构，前端`Vue3` + 后端`FastAPI`，支持多模型AI服务集成

# 📥 代码拉取

## 首次克隆项目

首次克隆时需要特别注意：

```bash
# 克隆主仓库
git clone https://github.com/domonic18/ai-pptist-system.git
cd ai-pptist-system

# 初始化并更新子模块
git submodule update --init --recursive
```

# 🚀 快速部署运行

## 开发环境快速启动

### 第一步：配置环境变量

复制并配置环境变量文件：

```bash
# 复制示例配置文件
cp config/.env.example config/.env

# 编辑配置文件，填入必要的配置项
# 包括：数据库连接、腾讯云COS密钥、应用密钥等
vim config/.env
```

### 第二步：启动数据库和Redis

使用Docker Compose启动基础服务：

```bash
# 启动PostgreSQL数据库和Redis
docker-compose -f docker-compose-dev.yml up -d
```

### 第三步：启动后端服务

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -e .

# 启动FastAPI服务（终端1）
uvicorn app.main:app --reload --port 8000

# 启动Celery Worker（终端2）
celery -A app.tasks.celery_app worker --loglevel=info
```

### 第四步：启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

浏览器访问：http://127.0.0.1:5173/

## 使用部署脚本

项目提供了自动化部署脚本 `scripts/deploy.sh`，用于管理生产环境和开发环境的部署。

> 详细使用说明请参考[部署脚本说明](scripts/README.md)

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


# 📚 功能列表

## AI智能生成功能
- **智能大纲生成**：基于主题自动生成PPT内容大纲，支持流式输出实时预览
- **Markdown文件上传**：支持上传.md格式文件，自动解析为PPT大纲
- **香蕉生成模式**：创新的一键生成功能，自动分析大纲结构并批量生成高质量幻灯片
- **文生图驱动**：集成先进的文生图模型，根据内容自动生成精美配图
- **多模型支持**：支持多种对话和图片生成模型，灵活配置
- **模板智能匹配**：根据内容自动推荐合适的幻灯片模板

## 图片管理功能
- **云端图片存储**：基于腾讯云COS的图片存储和管理
- **智能图片搜索**：支持按标签、关键词搜索图片
- **批量标签管理**：支持批量添加、编辑图片标签
- **图片生成**：集成AI图片生成服务
- **图片解析**：支持OCR文字识别和图片内容分析

## 核心编辑功能
- **完整的幻灯片编辑器**：支持文字、图片、形状、图表、表格等元素编辑
- **大纲可视化编辑**：支持点击编辑、右键添加/删除大纲项
- **多种导出格式**：支持PPTX、JSON、图片、PDF等格式导出
- **模板系统**：内置丰富的幻灯片模板，支持用户自定义模板
- **响应式设计**：支持移动端基础编辑和预览

## 模型管理功能
- **多模型配置**：支持配置多个对话和图片生成模型
- **API密钥加密**：安全的API密钥存储和管理
- **模型切换**：灵活切换不同的AI模型进行生成
- **默认模型设置**：设置默认使用的对话和图片生成模型


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
- [开发规范](docs/standard/README.md) - 包含API设计、响应格式、日志记录、测试规范等完整规范体系


# 📄 版权声明/开源协议

## 项目来源
本项目基于原 [PPTist](https://github.com/pipipi-pikachu/PPTist) 项目开发，向原项目作者 [pipipi-pikachu](https://github.com/pipipi-pikachu) 致敬。

原项目仓库：[https://github.com/pipipi-pikachu/PPTist](https://github.com/pipipi-pikachu/PPTist)

## 开源协议
[AGPL-3.0 License](/LICENSE) | Copyright © 2020-PRESENT [pipipi-pikachu](https://github.com/pipipi-pikachu)

## 贡献说明
欢迎开发者为本项目贡献代码，共同推进AI PPT应用的发展。