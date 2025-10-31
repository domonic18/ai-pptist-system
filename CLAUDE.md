# AI PPTist System - Claude Code AI 上下文文件 (claude-master)

## 1. 项目概览
- **愿景：** 构建一个基于AI的智能PPT编辑和生成系统，提供从主题到完整PPT的一键生成能力，结合云存储和智能图片管理
- **当前阶段：** 开发中期阶段，已完成核心AI生成功能、图片云存储管理、多模型支持，正在完善布局优化和用户体验
- **核心架构：** 前后端分离架构，前端使用Vue 3 + TypeScript + Vite，后端使用Python FastAPI + PostgreSQL + Redis，集成腾讯云COS存储
- **开发策略：** 渐进式架构升级，模块化设计，基于现有ai_presentation项目的成熟方案进行扩展

## 2. 项目结构

**⚠️ 重要：AI 智能体在执行任何任务前，必须先了解完整的技术栈和项目组织方式。**

AI PPTist System遵循前后端分离的现代Web应用架构。完整的技术栈和文件树结构如下：

### 技术栈概览
- **前端**: Vue 3 + TypeScript + Vite + Pinia + Element Plus
- **后端**: Python FastAPI + SQLAlchemy + PostgreSQL + Redis
- **存储**: 腾讯云COS + PostgreSQL + IndexedDB
- **AI集成**: OpenAI API + 多模型支持 + MLflow追踪
- **部署**: Docker + Docker Compose

### 核心模块
- **图片管理**: 上传、搜索、生成、删除、标签管理
- **AI生成**: 大纲生成、幻灯片生成、布局优化
- **模型管理**: 多AI模型配置、API密钥加密存储
- **模板系统**: 系统模板、用户自定义模板
- **布局优化**: 智能布局调整、用户自定义提示词支持

## 3. 编码规范与 AI 指令

### 通用指令
- 你最重要的工作是管理自己的上下文。在规划变更前，务必先阅读相关文件。
- 更新文档时，保持更新简洁明了，防止内容冗余。
- 编写代码遵循 KISS、YAGNI 和 DRY 原则。
- 有疑问时遵循经过验证的最佳实践。
- 未经用户批准不要提交到 git。
- 不要运行任何服务器，而是告诉用户运行服务器进行测试。
- 优先考虑行业标准库/框架，而不是自定义实现。
- 永远不要模拟任何东西。永远不要使用占位符。永远不要省略代码。
- 相关时应用 SOLID 原则。使用现代框架特性而不是重新发明解决方案。
- 对想法的好坏要坦率诚实。
- 让副作用明确且最小化。
- 设计数据库模式要便于演进（避免破坏性变更）。

### 文件组织与模块化
- 默认创建多个小而专注的文件，而不是大而单一的文件
- 每个文件应该有单一职责和明确目的
- 尽可能保持文件在 350 行以内 - 通过提取工具、常量、类型或逻辑组件到单独模块来拆分大文件
- 分离关注点：工具、常量、类型、组件和业务逻辑到不同文件
- 优先组合而非继承 - 只在真正的 'is-a' 关系中使用继承，在 'has-a' 或行为混合时优先组合

- 遵循现有项目结构和约定 - 将文件放在适当目录。必要时创建新目录并移动文件。
- 使用定义明确的子目录保持组织和可扩展性
- 用清晰的文件夹层次和一致的命名约定构建项目
- 正确导入/导出 - 为可重用性和可维护性而设计

### 类型提示（必需）
- **始终**为函数参数和返回值使用类型提示
- 对复杂类型使用 `from typing import`
- 优先使用 `Optional[T]` 而不是 `Union[T, None]`
- 对数据结构使用 Pydantic 模型

```python
# 良好示例
from typing import Optional, List, Dict, Tuple, Any

async def process_layout_optimization(
    elements: List[ElementData],
    canvas_size: CanvasSize,
    options: Optional[OptimizationOptions] = None,
    user_prompt: Optional[str] = None
) -> Tuple[List[ElementData], Dict[str, Any]]:
    """优化幻灯片布局。"""
    pass
```

### 命名约定
- **类**：PascalCase（例如 `AIModel`、`ImageRepository`）
- **函数/方法**：snake_case（例如 `generate_image`、`process_layout_optimization`）
- **常量**：UPPER_SNAKE_CASE（例如 `MAX_UPLOAD_SIZE`、`DEFAULT_IMAGE_QUALITY`）
- **私有方法**：前导下划线（例如 `_validate_input`、`_build_requirements`）
- **Pydantic 模型**：PascalCase 带 `Schema` 后缀（例如 `ImageResponseSchema`、`LayoutOptimizationRequestSchema`）
- **数据库模型**：PascalCase（例如 `AIModel`、`Image`）
- **API端点**：snake_case（例如 `generate_image`、`layout_optimization`）

### 文档要求
- 每个模块需要文档字符串
- 每个公共函数需要文档字符串
- 使用 Google 风格的文档字符串
- 在文档字符串中包含类型信息

```python
async def generate_image(
    prompt: str,
    generation_model: str = "dall-e-3",
    width: int = 1024,
    height: int = 1024,
    quality: str = "standard"
) -> Dict[str, Any]:
    """通过AI模型生成图片。

    Args:
        prompt: 图片描述提示词
        generation_model: 生成模型名称
        width: 图片宽度
        height: 图片高度
        quality: 图片质量

    Returns:
        包含图片信息的字典

    Raises:
        ValueError: 如果提示词为空或参数无效
        ModelNotFoundError: 如果指定的模型不存在
    """
    pass
```

### 安全优先
- 永远不要信任外部输入 - 在边界处验证一切
- 将秘钥保存在环境变量中，永远不要在代码中
- 记录安全事件（登录尝试、认证失败、速率限制、权限拒绝），但永远不要记录敏感数据（音频、对话内容、令牌、个人信息）
- 在 API 网关级别认证用户 - 永远不要信任客户端令牌
- 使用行级安全（RLS）在用户间强制数据隔离
- 设计认证以在所有客户端类型间一致工作
- 为你的平台使用安全的认证模式
- 在创建会话前在服务器端验证所有认证令牌
- 在存储或处理前清理所有用户输入

### 错误处理
- 使用具体异常而不是泛型异常
- 始终记录带上下文的错误
- 提供有用的错误消息
- 安全地失败 - 错误不应该暴露系统内部

### 可观测系统与日志标准
- 每个请求都需要关联 ID 用于调试
- 为机器而不是人类构建日志 - 使用 JSON 格式，带一致字段（时间戳、级别、关联 ID、事件、上下文）用于自动化分析
- 使跨服务边界的调试成为可能

### 状态管理
- 每个状态片段有一个真相来源
- 让状态变更明确且可追踪
- 为多服务语音处理而设计 - 使用会话 ID 进行状态协调，避免在服务器内存中存储对话数据
- 保持对话历史轻量（文本，不是音频）

### API 设计原则
- 带一致 URL 模式的 RESTful 设计
- 正确使用 HTTP 状态码
- 从第一天就版本化 API（/v1/、/v2/）
- 为列表端点支持分页
- 使用一致的 JSON 响应格式：
  - 成功：`{ "data": {...}, "error": null }`
  - 错误：`{ "data": null, "error": {"message": "...", "code": "..."} }`

## 4. 多智能体工作流与上下文注入

### 子智能体的自动上下文注入
当使用 Task 工具生成子智能体时，核心项目上下文（CLAUDE.md、项目结构、技术栈信息）会自动注入到它们的提示中。这确保所有子智能体都能立即访问基本项目文档，无需在每个 Task 提示中手动指定。

### 推荐使用的智能体类型
- **Explore**: 用于快速探索代码库结构，查找特定功能实现
- **general-purpose**: 用于复杂多步骤任务，需要深度代码分析和实现
- **template-management-expert**: 用于处理项目模板、示例代码和文档模板
- **chinese-localization-expert**: 用于文档翻译和界面汉化

### 智能体使用场景
- **代码探索**: 使用 Explore 智能体快速了解项目结构
- **功能实现**: 使用 general-purpose 智能体处理复杂业务逻辑
- **模板管理**: 使用 template-management-expert 处理PPT模板相关任务
- **国际化**: 使用 chinese-localization-expert 处理中文文档和界面

## 5. MCP 服务器集成

### Gemini 咨询服务器
**使用场景：**
- 需要深度分析或多种方法的复杂编码问题
- 代码审查和架构讨论
- 跨多个文件调试复杂问题
- 性能优化和重构指导
- 复杂实现的详细解释
- 高度安全相关任务

**自动上下文注入：**
- 项目配置和架构信息会自动包含在咨询会话中
- 确保Gemini全面理解项目的技术栈、架构和编码标准

**使用模式：**
```python
# 新咨询会话（项目上下文自动附加）
mcp__gemini__consult_gemini(
    specific_question="我应该如何优化这个图片生成管道？",
    problem_description="需要减少图片生成延迟，提高并发处理能力",
    code_context="当前管道顺序处理图片生成请求...",
    attached_files=[
        "backend/app/services/image/image_generation_service.py"  # 具体文件
    ],
    preferred_approach="optimize"
)

# 在现有会话中跟进
mcp__gemini__consult_gemini(
    specific_question="内存使用怎么办？",
    session_id="session_123",
    additional_context="实现了你的建议，现在看到高内存使用"
)
```

**关键能力：**
- 带上下文保持的持续对话会话
- 多文件分析的文件附加和缓存
- 专门的辅助模式（解决、审查、调试、优化、解释）
- 复杂多步问题的会话管理

**重要：**将 Gemini 的响应作为咨询反馈对待。批判性评估建议，将有价值的洞察整合到你的解决方案中，然后继续实现。

### Context7 文档服务器
**仓库**：[Context7 MCP 服务器](https://github.com/upstash/context7)

**使用场景：**
- 使用外部库/框架（Vue 3、FastAPI、PostgreSQL等）
- 需要超出训练截止日期的当前文档
- 实现与第三方工具的新集成或功能
- 排查库特定问题

**使用模式：**
```python
# 将库名解析为Context7 ID
mcp__context7__resolve_library_id(libraryName="vue")

# 获取焦点文档
mcp__context7__get_library_docs(
    context7CompatibleLibraryID="vuejs/vue",
    topic="composition-api",
    tokens=8000
)
```

**关键能力：**
- 最新库文档访问
- 主题焦点文档检索
- 支持特定库版本
- 与当前开发实践集成

## 6. 项目规范体系

**⚠️ 重要：所有开发工作必须遵循项目的统一规范体系。在执行具体任务前，请先查阅相关规范文档。**

### 6.1 API 设计与实现规范
- **文件路径**: `docs/standard/API设计与实现规范.md`
- **内容**: 统一的设计原则、分层架构、路由管理、代码实现规范
- **适用**: 所有 API 的设计、开发和维护
- **核心要点**:
  - 轻路由、重服务的分层架构
  - 端点层、处理器层、服务层、仓库层分离
  - 统一的异常处理和错误码体系

### 6.2 API 响应与日志规范
- **文件路径**: `docs/standard/API响应与日志规范.md`
- **内容**: 统一的响应格式、错误处理、状态码规范、日志记录标准
- **适用**: 所有 API 的响应格式和日志记录
- **核心要点**:
  - 标准响应格式：`StandardResponse` 结构
  - 统一的错误码和错误详情格式
  - 结构化日志记录和消息模板管理

### 6.3 前端 API 配置规范
- **文件路径**: `docs/standard/前端API配置说明.md`
- **内容**: 前端API端点集中管理规范
- **适用**: 前端API配置管理和使用
- **核心要点**:
  - API端点统一在 `frontend/src/configs/api.ts` 中管理
  - 避免硬编码API路径
  - 支持类型安全和易于重构

### 6.4 测试用例维护规范
- **文件路径**: `backend/tests/README.md`
- **内容**: 测试框架指南、分层测试架构、单元测试和集成测试规范
- **适用**: 所有后端测试用例的编写和维护
- **核心要点**:
  - 分层测试架构（单元测试 + 集成测试）
  - 统一的测试配置管理
  - 专用运行脚本支持
  - 丰富的 Mock 工具和测试数据管理

### 6.5 前端交互设计规范
- **文件路径**: `docs/design/frontend-interaction-design-specification.md`
- **内容**: 完整的前端设计系统，包含颜色、字体、间距、组件、交互等规范
- **适用**: 所有前端界面设计和开发
- **核心要点**:
  - 设计原则：一致性、可访问性、效率性、反馈性、容错性
  - 颜色系统：主色调、中性色、功能色
  - 字体系统：字体家族、大小、粗细、行高
  - 间距系统：基础间距单位和倍数
  - 组件规范：按钮、输入框、对话框等
  - 交互规范：动画、状态反馈、键盘交互

### 6.6 规范实施要求

#### 后端要求
1. 所有新开发的 API 必须遵循 API 设计规范
2. 错误处理使用统一错误码体系
3. 响应必须包含时间戳和请求 ID
4. 分页接口必须遵循分页规范
5. 所有日志记录必须使用统一的日志系统
6. 编写符合规范的测试用例

#### 前端要求
1. 统一处理响应结构解析
2. 错误处理基于标准错误码
3. 请求追踪使用请求 ID
4. 支持多语言错误消息显示
5. 遵循前端交互设计规范
6. 使用统一的 API 配置管理

## 7. 任务完成后协议
完成任何编码任务后，遵循此检查清单：

### 1. 类型安全与质量检查
根据修改内容运行适当命令：
- **Python 项目**：运行 mypy 类型检查
- **TypeScript 项目**：运行 tsc --noEmit
- **前端项目**：运行 npm run type-check
- **后端项目**：运行 pytest 确保测试通过

### 2. 代码质量检查
- 运行代码格式化工具确保代码风格一致
- 检查是否有未使用的导入或变量
- 确保所有新增功能都有相应的测试覆盖

### 3. 验证
- 确保所有类型检查通过后再认为任务完成
- 如果发现类型错误，在标记任务完成前修复它们
- 确保API端点的输入验证和错误处理正确
- 验证数据库迁移脚本的正确性

### 4. 文档更新
- 更新相关API文档（如有需要）
- 确保代码注释和文档字符串保持最新
- 更新CLAUDE.md文件中的相关信息（如新增功能）

# 重要指令提醒
按要求做；不多不少。
除非绝对必要以实现目标，否则永远不要创建文件。
始终优先编辑现有文件而不是创建新文件。
除非用户明确要求，否则永远不要主动创建文档文件（*.md）或 README 文件。只有在用户明确要求时才创建文档文件。

## 项目特定注意事项
- **前后端分离**: 注意前端和后端的分离架构，确保API接口设计合理
- **图片管理**: 所有图片操作都要考虑腾讯云COS集成
- **AI模型配置**: 注意API密钥的加密存储和多模型支持
- **布局优化**: 新增布局优化功能时要考虑用户自定义提示词支持
- **数据库**: 使用PostgreSQL的JSONB特性存储幻灯片模板数据
- **Docker部署**: 所有服务都支持Docker容器化部署