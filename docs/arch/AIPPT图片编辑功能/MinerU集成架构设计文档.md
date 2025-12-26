# AIPPT生成PPT增强流程 - MinerU集成架构设计文档

## 版本信息

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| v1.0 | 2025-12-26 | Claude Code | 初始版本 |
| v1.1 | 2025-12-26 | Claude Code | 修正API URL（v1非v4），添加原始资料备注，完善MinerU API说明 |
| v1.2 | 2025-12-26 | Claude Code | **重要修正**：MinerU不提供样式信息，改为MinerU+多模态混合模式 |
| v1.3 | 2025-12-26 | Claude Code | **关键问题解决方案**：1) 文字去重算法设计 2) MinerU异步API与Celery架构方案 |
| v1.4 | 2025-12-26 | Claude Code | **重大修正**：修正API为v4端点，添加ZIP文件下载流程，修正content_list.json结构定义 |

---

## 1. 背景与问题分析

### 1.1 当前系统问题

**问题1：坐标位置不准确**
- 混合OCR识别（百度OCR + 多模态大模型）后的文字坐标位置可能存在偏差
- 相比原始图片中的文字位置，渲染时有时偏下、有时偏右
- 影响前端文字组件的正确定位

**问题2：文字重复显示**
- 混合OCR融合时，百度OCR和多模态大模型识别的结果可能存在重复
- 数据去重逻辑复杂，容易出现遗漏或误删

**问题3：装饰性元素无法识别**
- 当前只能识别文字元素
- 图片中的装饰性图形（如图标、装饰线条、背景图案等）无法识别
- 限制了用户对完整PPT的编辑能力

### 1.2 解决方案概述

**核心方案：MinerU + 多模态大模型混合模式**

| 需求 | 原方案 | 新方案 |
|------|--------|--------|
| 文字坐标识别 | 百度OCR | MinerU API（高精度） |
| 装饰元素识别 | 不支持 | MinerU API（新增） |
| 文字样式识别 | 多模态大模型 | 多模态大模型（保持） |
| 文字内容识别 | 百度OCR + 多模态 | MinerU API（主）+ 多模态（校验） |
| 文字去除 | 文生图大模型 | 保持不变（文生图） |

**方案说明**：
由于MinerU API不提供文字样式信息（字体、颜色、大小），需要采用混合模式：
- **MinerU**：提供精确的文字坐标、装饰元素识别
- **多模态大模型**：提供文字样式信息
- **融合层**：将MinerU的坐标与多模态的样式融合

**保留原有功能**
- 腾讯OCR、百度OCR、混合识别功能保留（可通过配置切换）
- 文生图文字去除功能保持不变
- 前端渲染和编辑逻辑不变

---

## 2. MinerU 技术概述

### 2.1 MinerU 简介

**MinerU** 是由上海人工智能实验室 OpenDataLab 团队开发的一站式文档解析工具，支持 PDF、Word、PPT、图片等多种格式的智能数据提取。

**核心能力**：
- **高精度文字识别**：结合布局分析和OCR，实现像素级精确定位
- **结构化元素识别**：识别文本块/标题/图片/表格/公式等内容块，并输出结构化数据与坐标
- **装饰元素识别**：识别图片、图标、装饰线条、背景图案等
- **结构化输出**：返回JSON格式，包含所有元素的精确坐标和属性

> **重要更正（与本文后续保持一致）**：在 MinerU 的在线 API（v4）结构化输出中，通常**不包含**我们在 PPT 编辑中需要的文字样式信息（如字体、字号、颜色、对齐）。因此本文采用 **MinerU（坐标/结构）+ 多模态（样式）** 的混合策略，由多模态补全样式信息。

### 2.2 MinerU API 调用方式

> **原始资料**: [MinerU API文档](https://mineru.net/apiManage/docs)，详情参考：`docs/arch/AIPPT图片编辑功能/MinerU.pdf`

**在线 API 调用**：

#### 2.2.1 创建识别任务

> **原始资料**: [MinerU API文档](https://mineru.net/apiManage/docs)，详情参考：`docs/arch/AIPPT图片编辑功能/MinerU.pdf`

**请求端点**: `POST https://mineru.net/api/v4/extract/task`

**请求头**:
```http
Content-Type: application/json
Authorization: Bearer {token}
```

**请求参数**:
```json
{
  "url": "文档URL（支持PDF、图片等格式）",
  "model_version": "vlm",
  "is_ocr": true,
  "enable_formula": true,
  "enable_table": true,
  "page_ranges": "1-10"
}
```

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `url` | string | 是 | 待识别文档的URL | - |
| `model_version` | string | 否 | 模型版本：vlm 或 pipeline | "vlm" |
| `is_ocr` | boolean | 否 | 是否开启OCR | false |
| `enable_formula` | boolean | 否 | 是否识别公式 | true |
| `enable_table` | boolean | 否 | 是否识别表格 | true |
| `language` | string | 否 | 文档语言 | "ch" |
| `page_ranges` | string | 否 | 页码范围（如"1-10"） | - |
| `data_id` | string | 否 | 自定义数据ID | - |
| `callback` | string | 否 | 回调URL | - |
| `extra_formats` | array | 否 | 额外输出格式 | ["docx","html"] |
| `seed` | string | 否 | 回调签名密钥 | - |

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "task_id": "a90e6ab6-44f3-4554-b459b62fe4c6b436"
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
```

#### 2.2.2 查询任务状态

**请求端点**: `GET https://mineru.net/api/v4/extract/task/{task_id}`

**请求头**:
```http
Authorization: Bearer {token}
```

**响应示例 - 处理中**:
```json
{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "running",
    "err_msg": "",
    "extract_progress": {
      "extracted_pages": 1,
      "total_pages": 2,
      "start_time": "2025-01-20 11:43:20"
    }
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
```

**响应示例 - 处理完成**:
```json
{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "done",
    "full_zip_url": "https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip",
    "err_msg": ""
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
```

**状态值说明**:
- `running`: 处理中，包含 `extract_progress` 信息
- `done`: 处理完成，包含 `full_zip_url` 下载链接
- `failed`: 处理失败，包含 `err_msg` 错误信息

#### 2.2.3 下载识别结果（ZIP文件）

**重要说明**：MinerU API 完成后返回的是 **ZIP 文件下载链接**，不是直接返回识别结果数据。

**下载流程**：
1. 查询任务状态，当 `state == "done"` 时获取 `full_zip_url`
2. 下载 ZIP 文件
3. 解压 ZIP 文件
4. 读取 `content_list.json` 获取识别结果

**ZIP 文件结构**：
```
{原文件名}.zip
├── content_list.json    # 主要识别结果（我们需要的）
├── model.json           # 模型推理结果
├── middle.json          # 中间处理结果
├── {原文件名}.md        # Markdown 输出
├── images/              # 提取的图片目录
│   ├── xxx.jpg
│   └── ...
└── layout.pdf           # 布局分析可视化
```

**本系统实际使用哪些文件（建议/MVP口径）**：
- **必须**：`content_list.json`（按阅读顺序平铺的内容块；用于提取文本块、图片块、公式/表格等以及对应 bbox）
- **按需**：`images/`（当需要把 MinerU 识别出的图片/装饰元素做“可编辑元素”时使用 `img_path` 指向的资源）
- **可选**：`model.json` / `middle.json` / `layout.pdf`（主要用于调试/对齐复杂布局；MVP 可以不依赖它们）
- **原图尺寸来源（与现有代码一致）**：后端通过 `cos_key` 生成预签名 URL 下载原图，用 PIL 读取真实 `image_width/image_height` 并回传到 `metadata`，用于把 `content_list.json` 的 0-1000 bbox 还原为像素坐标。

#### 2.2.4 Python调用示例

```python
import requests
import zipfile
import io
import json

token = "YOUR_MINERU_TOKEN"
file_url = "https://example.com/document.pdf"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

# 步骤1: 创建任务
request_data = {
    "url": file_url,
    "model_version": "vlm",
    "is_ocr": True,
    "enable_formula": True,
    "enable_table": True
}

response = requests.post(
    url="https://mineru.net/api/v4/extract/task",
    headers=headers,
    json=request_data
)

result = response.json()
if result.get("code") == 0:
    task_id = result["data"]["task_id"]
    print(f"任务已创建，ID: {task_id}")

    # 步骤2: 轮询任务状态
    while True:
        status_response = requests.get(
            url=f"https://mineru.net/api/v4/extract/task/{task_id}",
            headers=headers
        )
        status_data = status_response.json()["data"]
        state = status_data.get("state")

        if state == "done":
            zip_url = status_data.get("full_zip_url")
            print(f"任务完成，下载结果: {zip_url}")

            # 步骤3: 下载并解压ZIP文件
            zip_response = requests.get(zip_url)
            zip_file = zipfile.ZipFile(io.BytesIO(zip_response.content))

            # 步骤4: 读取content_list.json
            with zip_file.open("content_list.json") as f:
                content_list = json.load(f)

            print(f"识别到 {len(content_list)} 个内容块")
            break

        elif state == "running":
            progress = status_data.get("extract_progress", {})
            print(f"处理中: {progress.get('extracted_pages', 0)}/{progress.get('total_pages', 0)}")
            import time
            time.sleep(5)

        else:  # failed
            print(f"任务失败: {status_data.get('err_msg')}")
            break
```

> **注意**:
> - API版本是 **v4** 不是 v1
> - 完成后需要下载ZIP文件
> - ZIP文件中包含 `content_list.json` 是主要的识别结果
> - 单个文件限制：200MB / 600页
> - 每个账号每天享有 2000 页最高优先级解析额度

### 2.3 MinerU 输出格式（content_list.json）

> **原始资料**: [MinerU输出文件格式](https://opendatalab.github.io/MinerU/zh/reference/output_files/)，详情参考：`docs/arch/AIPPT图片编辑功能/MinerU输出文件格式.pdf`

**重要说明**：
1. MinerU API 完成后返回 ZIP 文件下载链接
2. ZIP 文件中包含 `content_list.json` 是主要的识别结果
3. **不提供**文字的样式信息（字体、颜色、大小等），只提供：文字内容、精确坐标、类型

#### 2.3.1 VLM 后端 content_list.json 结构

```json
[
  {
    "type": "text",
    "text": "人工智能技术发展现状",
    "text_level": 1,
    "bbox": [62, 480, 946, 904],
    "page_idx": 0
  },
  {
    "type": "image",
    "img_path": "images/a8ecda1c69b27e4f79fce1589175a9d721cbdc1cf78b4cc06a015f3746f6b9d8.jpg",
    "image_caption": ["Fig. 1. Annual flow duration curves"],
    "image_footnote": [],
    "bbox": [62, 480, 946, 904],
    "page_idx": 1
  },
  {
    "type": "equation",
    "img_path": "images/181ea56ef185060d04bf4e274685f3e072e922e7b839f093d482c29bf89b71e8.jpg",
    "text": "$$\nQ _ { \\% } = f ( P ) + g ( T )\n$$",
    "text_format": "latex",
    "bbox": [62, 480, 946, 904],
    "page_idx": 2
  },
  {
    "type": "table",
    "table_caption": ["Table 1. Experimental results"],
    "table_footnote": [],
    "html": "<table>...</table>",
    "bbox": [62, 480, 946, 904],
    "page_idx": 3
  },
  {
    "type": "code",
    "sub_type": "algorithm",
    "code_caption": ["Algorithm 1 Modules for MCTSteg"],
    "code_body": "1: function GETCOORDINATE(d)\n2: $x \\gets d / l$...",
    "bbox": [510, 87, 881, 740],
    "page_idx": 0
  }
]
```

#### 2.3.2 字段说明

**通用字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 内容类型：text, title, image, table, equation, code, list 等 |
| `bbox` | array | 边界框 `[x0, y0, x1, y1]`。**在 content_list.json 中（官方说明）映射在 0-1000 范围**，需要结合真实图片尺寸（优先：后端 PIL 读取；或 `page_info.width/height` 若可用）还原为像素坐标 |
| `page_idx` | int | 页码（从 0 开始） |

**文本类型字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 文字内容 |
| `text_level` | int | 文本层级：0=正文, 1=一级标题, 2=二级标题 |

**图片类型字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `img_path` | string | 图片文件路径（相对于ZIP根目录） |
| `image_caption` | array | 图片描述文本列表 |
| `image_footnote` | array | 图片脚注列表 |

**公式类型字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `img_path` | string | 公式图片路径 |
| `text` | string | LaTeX 格式公式 |
| `text_format` | string | 格式类型：latex |

**表格类型字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `table_caption` | array | 表格描述列表 |
| `table_footnote` | array | 表格脚注列表 |
| `html` | string | HTML 格式表格 |

**代码类型字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `sub_type` | string | 子类型：code 或 algorithm |
| `code_caption` | array | 代码描述列表 |
| `code_body` | string | 代码内容 |

#### 2.3.3 坐标说明

- **bbox 格式**：`[x0, y0, x1, y1]`（左上角和右下角坐标）
- **坐标映射（content_list.json）**：bbox 为 0-1000 归一化范围，需要根据真实图片尺寸转换为像素坐标（\(x_{px}=x/1000 \cdot W,\ y_{px}=y/1000 \cdot H\)）
- **坐标系**：以页面左上角为原点 (0, 0)

#### 2.3.4 支持的内容类型（VLM后端）

| type | 说明 |
|------|------|
| `text` | 正文文本 |
| `title` | 标题 |
| `equation` | 行间公式 |
| `image` | 图片 |
| `image_caption` | 图片描述 |
| `image_footnote` | 图片脚注 |
| `table` | 表格 |
| `table_caption` | 表格描述 |
| `table_footnote` | 表格脚注 |
| `code` | 代码块 |
| `list` | 列表 |
| `header` | 页眉 |
| `footer` | 页脚 |
| `page_number` | 页码 |

### 2.4 混合识别模式

由于MinerU不提供样式信息，本系统采用**混合识别模式**：

| 识别项 | 使用方案 | 输出内容 |
|--------|---------|----------|
| 文字坐标 | MinerU API | 精确bbox坐标 |
| 装饰元素 | MinerU API | 图片位置和路径 |
| 文字样式 | 多模态大模型 | 字体、颜色、大小 |
| 文字内容 | MinerU API（主）+ 多模态（校验） | 文字内容 |

**融合策略**：
1. 使用MinerU获取精确的文字坐标和装饰元素位置
2. 使用多模态大模型（GPT-4V/Claude Vision）识别文字样式信息
3. 通过位置匹配融合两种结果
4. 输出包含坐标和样式的完整数据

---

## 3. 整体架构设计

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              前端层 (Vue 3 + TypeScript)                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                    编辑器视图 (Editor/CanvasTool/index.vue)                    │   │
│  │                                                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    工具栏按钮 [解析图片]                              │    │   │
│  │  └──────────────────────────────────────────────────────────────────────┘    │   │
│  │                                                                              │   │
│  │  ┌──────────────────────────────────────────────────────────────────────┐    │   │
│  │  │                        画布容器 (Canvas)                               │    │   │
│  │  │                                                                        │    │   │
│  │  │  ┌────────────────────────────────────────────────────────────────┐   │    │   │
│  │  │  │              背景图片层 (处理后的无文字图片)                      │   │    │   │
│  │  │  └────────────────────────────────────────────────────────────────┘   │    │   │
│  │  │                              │                                        │    │   │
│  │  │                              ▼                                        │    │   │
│  │  │  ┌────────────────────────────────────────────────────────────────┐   │    │   │
│  │  │  │                  元素层 (可编辑元素)                              │   │    │   │
│  │  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │    │   │
│  │  │  │  │ 文字元素1 │  │ 图片元素2 │  │ 文字元素3 │  │ 装饰元素4 │  ...   │   │    │   │
│  │  │  │  │ (可编辑)  │  │ (可编辑)  │  │ (可编辑)  │  │ (可编辑)  │        │   │    │   │
│  │  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │    │   │
│  │  │  └────────────────────────────────────────────────────────────────┘   │    │   │
│  │  └──────────────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                   图片编辑服务 (imageEditingService.ts)                       │   │
│  │  - parseWithMinerU()       - parseWithHybridOCR()                            │   │
│  │  - removeTextFromImage()   - applyImageEdit()                               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ HTTP/WebSocket
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            API网关层 (FastAPI)                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                   图片编辑端点 (image_editing.py)                             │  │
│  │                                                                              │  │
│  │  POST /api/v1/image_editing/parse_with_mineru       MinerU识别               │  │
│  │  POST /api/v1/image_editing/parse_hybrid_ocr        混合OCR识别              │  │
│  │  POST /api/v1/image_editing/remove_text            文生图去除文字             │  │
│  │  GET  /api/v1/image_editing/status/{task_id}       查询任务状态              │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
┌───────────────────────────────┐                   ┌───────────────────────────────┐
│      MinerU API层             │                   │      文生图引擎层              │
├───────────────────────────────┤                   ├───────────────────────────────┤
│                               │                   │                               │
│  ┌─────────────────────────┐ │                   │  ┌─────────────────────────┐ │
│  │  MinerU 在线API         │ │                   │  │  文生图大模型            │ │
│  │  - 高精度文字识别        │ │                   │  │  - DALL-E 3             │ │
│  │  - 装饰元素识别          │ │                   │  │  - Stable Diffusion     │ │
│  │  - 结构化输出（坐标/类型）│ │                   │  │  - Inpaint功能          │ │
│  │  - 像素级坐标定位        │ │                   │  └─────────────────────────┘ │
│  └─────────────────────────┘ │                   │                               │
│                               │                   │                               │
└───────────────────────────────┘                   └───────────────────────────────┘
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            服务层 (Services)                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐            │
│  │   MinerU识别服务             │    │   任务管理服务                   │            │
│   │                              │    │                                   │            │
│  │ - parse_with_mineru()        │    │ - create_task()                  │            │
│  │ - format_mineru_result()     │    │ - update_status()                │            │
│  │ - convert_to_text_regions()  │    │ - save_result()                  │            │
│  │ - convert_to_image_regions() │    │ - get_task_progress()            │            │
│  └─────────────────────────────┘    └─────────────────────────────────┘            │
│                                                                                      │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐            │
│  │   文字去除服务               │    │   配置管理服务                   │            │
│   │                              │    │                                   │            │
│  │ - remove_text_via_ai()       │    │ - get_ocr_engine_config()        │            │
│  │ - build_removal_prompt()     │    │ - is_text_removal_enabled()      │            │
│  └─────────────────────────────┘    └─────────────────────────────────┘            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            存储层 (Storage)                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────┐  ┌───────────────┐  ┌─────────────────────────────────────┐       │
│  │ PostgreSQL  │  │    Redis      │  │         腾讯云COS                    │       │
│  │             │  │               │  │                                     │       │
│  │ - 编辑任务  │  │ - 任务状态    │  │ - 原始图片                          │       │
│  │ - 识别结果  │  │ - 解析结果    │  │ - 处理后的图片                      │       │
│  │ - 装饰元素  │  │ - 缓存数据    │  │ - 提取的装饰图片                    │       │
│  │ - 配置信息  │  │ - 进度信息    │  │                                     │       │
│  └─────────────┘  └───────────────┘  └─────────────────────────────────────┘       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流图

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ 用户选择  │ → │ 前端调用 │ → │ 后端接收 │ → │ 创建任务 │ → │ 调用MinerU│
│ 图片编辑  │   │ API接口  │   │ 请求     │   │ 返回ID   │   │ API识别   │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │              │
     │              │              ▼              │              │
     │              │         ┌─────────┐         │              │
     │              │         │ 保存任务 │         │              │
     │              │         │ 到数据库 │         │              │
     │              │         └────┬────┘         │              │
     │              │              │              │              ▼
     │              │              │              │    ┌──────────────────────┐
     │              │              │              │    │ MinerU API          │
     │              │              │              │    │ - 文字识别          │
     │              │              │              │    │ - 装饰元素识别      │
     │              │              │              │    │ - 坐标定位          │
     │              │              │              │    │ - 结构化输出        │
     │              │              │              │    └──────┬───────────────┘
     │              │              │              │           │
     │              │              │              ▼           ▼
     │              │              │         ┌──────────────────────────────┐
     │              │              │         │ 格式化识别结果                │
     │              │              │         │ - 文字区域 (TextRegion)      │
     │              │              │         │ - 装饰元素 (ImageRegion)     │
     │              │              │         │ - 统一坐标格式               │
     │              │              │         └────────────┬─────────────────┘
     │              │              │                      │
     │              │              ▼                      ▼
     │              │         ┌────────────────────────────────────┐
     │              │         │ 保存识别结果到Redis/数据库          │
     │              │         └────────────┬───────────────────────┘
     │              │                      │
     │              │                      ▼
     │              │         ┌──────────────────────────────┐
     │              │         │ 检查配置：是否去除文字        │
     │              │         └────────────┬─────────────────┘
     │              │                      │
     │              │           ┌──────────┴──────────┐
     │              │           ▼                     ▼
     │              │    [启用文字去除]         [禁用文字去除]
     │              │           │                     │
     │              │           ▼                     ▼
     │              │    ┌─────────────┐      ┌─────────────┐
     │              │    │ 调用文生图   │      │ 跳过文字去除 │
     │              │    │ 去除文字     │      │ 保持原图     │
     │              │    └──────┬──────┘      └──────┬──────┘
     │              │           │                     │
     │              ▼           ▼                     ▼
     │         ┌────────────────────────────────────┐
     └─────────│ 前端接收完整结果                   │
               │ - 识别结果（文字+装饰元素）        │
               │ - 处理后的图片（可选）             │
               └────────────┬───────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ 前端坐标转换与渲染  │
                  │ - 转换MinerU坐标   │
                  │ - 创建文字元素     │
                  │ - 创建图片元素     │
                  │ - 应用样式信息（来自多模态） │
                  └─────────────────────┘
```

---

## 4. 核心实现流程与时序图

### 4.1 完整识别流程时序图

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐
│  前端   │    │ API网关 │    │ 服务层  │    │MinerU API│    │  文生图 │    │ 存储   │
└────┬────┘    └────┬────┘    └────┬────┘    └─────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │              │              │
     │ [1]点击解析  │              │              │              │              │
     │ 图片按钮     │              │              │              │              │
     │─────────────>│              │              │              │              │
     │              │              │              │              │              │
     │              │ [2]创建任务  │              │              │              │
     │              │─────────────>│              │              │              │
     │              │              │              │              │              │
     │              │              │ [3]保存任务  │              │              │
     │              │              │─────────────────────────────────────────>│
     │              │              │              │              │              │
     │              │<────────────│              │              │              │
     │              │ 返回task_id │              │              │              │
     │<─────────────│              │              │              │              │
     │              │              │              │              │              │
     │<─────────────│ [4]返回响应  │              │              │              │
     │              │              │              │              │              │
     │              │              │ [5]调用MinerU│              │              │
     │              │              │────────────────────────────>│              │
     │              │              │              │              │              │
     │              │              │              │ [6]处理图片  │              │
     │              │              │              │<─────────────│              │
     │              │              │              │              │              │
     │              │              │              │ [7]返回结果  │              │
     │              │              │<────────────────────────────│              │
     │              │              │              │              │              │
     │              │              │ [8]格式化结果│              │              │
     │              │              │─────────────>│              │              │
     │              │              │              │              │              │
     │              │              │ [9]保存结果  │              │              │
     │              │              │─────────────────────────────────────────>│
     │              │              │              │              │              │
     │              │              │ [10]检查配置 │              │              │
     │              │              │ 是否去除文字 │              │              │
     │              │              │<─────────────────────────────────────────>│
     │              │              │              │              │              │
     │              │              │      ┌───────┴───────┐                   │
     │              │              │      ▼               ▼                   │
     │              │              │   [启用]         [禁用]                  │
     │              │              │      │               │                   │
     │              │              │      ▼               │                   │
     │              │              │ [11]调用文生图    │                   │
     │              │              │─────────────────────────────────────────>│
     │              │              │              │              │              │
     │              │              │              │<─────────────│              │
     │              │              │<─────────────│ [12]返回图片 │              │
     │              │              │              │              │              │
     │              │              │ [13]更新任务状态 │              │           │
     │              │              │─────────────────────────────────────────>│
     │              │              │              │              │              │
     │              │ [14]前端轮询状态 │              │              │           │
     │              │<─────────────│              │              │              │
     │              │              │              │              │              │
     │<─────────────│ 返回完整结果  │              │              │              │
     │              │              │              │              │              │
     │ [15]应用结果 │              │              │              │              │
     │ - 转换坐标   │              │              │              │              │
     │ - 创建元素   │              │              │              │              │
     │ - 替换图片   │              │              │              │              │
     │              │              │              │              │              │
     ▼              ▼              ▼              ▼              ▼              ▼
```

### 4.2 坐标转换时序图

```
┌─────────┐    ┌─────────┐    ┌────────────────┐    ┌─────────┐
│ 前端    │    │ MinerU  │    │ 坐标转换服务   │    │ 画布    │
└────┬────┘    └────┬────┘    └───────┬────────┘    └────┬────┘
     │              │                  │                  │
     │ [1]提供目标渲染矩形(targetRect) │                  │
     │（选中图片元素的left/top/width/height）│              │
     │──────────────────────────────>│                  │
     │              │                  │（原图尺寸来自后端识别元数据：image_width/image_height）│
     │              │                  │                  │
     │              │ [2]返回识别结果  │                  │
     │              │ 包含bbox坐标     │                  │
     │<─────────────│                  │                  │
     │              │                  │                  │
     │ [3]提交坐标  │                  │                  │
     │ 转换请求     │                  │                  │
     │──────────────────────────────>│                  │
     │              │                  │                  │
     │              │                  │ [4]获取画布尺寸  │
     │              │                  │<─────────────────│
     │              │                  │                  │
     │              │                  │ [5]执行坐标转换（必须考虑图片渲染模式与文本盒模型） │
     │              │                  │                  │
     │              │                  │ ① 图片坐标映射（与前端 SmartImage 一致）         │
     │              │                  │ - 如果图片使用 object-fit: cover + center：      │
     │              │                  │   scale = max(dstW/srcW, dstH/srcH)              │
     │              │                  │   offsetX = (srcW*scale - dstW)/2                │
     │              │                  │   offsetY = (srcH*scale - dstH)/2                │
     │              │                  │   x' = dstLeft + x*scale - offsetX               │
     │              │                  │   y' = dstTop  + y*scale - offsetY               │
     │              │                  │ - 如果使用 contain：scale=min(...)，同样计算offset│
     │              │                  │ ② 文本元素盒模型补偿（PPT文本组件存在padding等）  │
     │              │                  │ - 现有 TextElement 默认 padding=10px，会使文字视觉 │
     │              │                  │   上系统性偏右/偏下；MVP建议 OCR 文本使用“紧贴模式” │
     │              │                  │   （padding=0，paragraphSpace=0，lineHeight≈1.0~1.2） │
     │              │                  │ - 若不改组件，则在插入时做反向补偿：               │
     │              │                  │   left -= padding; top -= padding; width += 2p; height += 2p │
     │              │                  │                  │
     │              │                  │ convert_bbox() {   │
     │              │                  │   [x1, y1, x2, y2] ->  │
     │              │                  │   {left, top, width, height} │
     │              │                  │ }                  │
     │              │                  │                  │
     │<──────────────────────────────│ [6]返回转换后坐标│
     │              │                  │                  │
     │ [7]创建元素  │                  │                  │
     │──────────────────────────────>│                  │
     │              │                  │                  │
     │              │                  │                  │
     ▼              ▼                  ▼                  ▼
```

> **关键结论（对应问题1）**：坐标偏移通常不是“识别引擎单点问题”，而是“坐标系 + 渲染模式 + 盒模型”未闭环。即便 MinerU 提供高精度 bbox（`content_list.json` 为 0-1000 归一化，按真实图片尺寸还原后），如果前端图片是 `object-fit: cover` 且文本组件有 padding，也会出现明显偏移。

---

## 5. 关键问题解决方案

### 5.1 问题1：文字去重方案

#### 5.1.1 当前问题分析

> **问题根源**: 分析当前 `hybrid_ocr_fusion.py` 代码发现，文字重复问题出现在多模态独有结果处理逻辑中（lines 267-278）：

```python
# 检查多模态独有结果（传统OCR遗漏的）
for multi_idx, multi_region in enumerate(multimodal_regions):
    if multi_idx not in matched_multimodal_indices:
        merged.append(HybridTextRegion(...))  # ⚠️ 可能造成重复
```

**问题原因**：
1. `matched_multimodal_indices` 只记录了成功匹配的多模态结果索引
2. 未匹配的多模态结果直接添加，未检查与传统OCR结果的重叠
3. 匹配阈值 0.7 可能过低，导致误匹配
4. 多模态结果可能与传统OCR结果位置重叠但内容略有差异，造成重复

#### 5.1.2 去重算法设计

**核心策略**：严格重叠检测 + 多阶段去重

**MVP建议（先止血，后增强）**：
- **默认不追加**“multimodal-only（传统/MinerU未命中）”的文字区域：以 MinerU/传统 OCR 的文本与坐标为主干，多模态只做样式补全。
- 只有在明确需要“补漏字”时，才允许追加 multimodal-only，并且必须先经过 IoU/中心点距离/文本相似度的去重检测。

```python
class TextDeduplicator:
    """
    文字去重器

    使用多重策略确保文字不会重复：
    1. IoU (Intersection over Union) 重叠检测
    2. 文字内容相似度检测
    3. 中心点距离检测
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        text_similarity_threshold: float = 0.85,
        distance_threshold: float = 50.0
    ):
        self.iou_threshold = iou_threshold
        self.text_similarity_threshold = text_similarity_threshold
        self.distance_threshold = distance_threshold

    def is_duplicate(
        self,
        region1: HybridTextRegion,
        existing_regions: List[HybridTextRegion]
    ) -> Tuple[bool, Optional[HybridTextRegion]]:
        """
        检查区域是否与已存在区域重复

        Args:
            region1: 待检测区域
            existing_regions: 已存在的区域列表

        Returns:
            (is_duplicate, matched_region): 是否重复，匹配的已存在区域
        """
        for existing in existing_regions:
            # 策略1: 检测bbox重叠 (IoU)
            iou = self._calculate_iou(region1.bbox, existing.bbox)
            if iou > self.iou_threshold:
                # 有重叠，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    region1.text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    return True, existing

            # 策略2: 检测中心点距离
            dist = self._calculate_center_distance(region1.bbox, existing.bbox)
            if dist < self.distance_threshold:
                # 距离很近，检查文字相似度
                text_sim = self._calculate_text_similarity(
                    region1.text,
                    existing.text
                )
                if text_sim > self.text_similarity_threshold:
                    return True, existing

        return False, None

    def _calculate_iou(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """
        计算两个边界框的IoU (Intersection over Union)

        IoU = 交集面积 / 并集面积
        """
        # 计算交集区域
        x_left = max(bbox1.x, bbox2.x)
        y_top = max(bbox1.y, bbox2.y)
        x_right = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y_bottom = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # 计算并集面积
        bbox1_area = bbox1.width * bbox1.height
        bbox2_area = bbox2.width * bbox2.height
        union_area = bbox1_area + bbox2_area - intersection_area

        if union_area == 0:
            return 0.0

        return intersection_area / union_area

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（使用编辑距离）"""
        import Levenshtein
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        distance = Levenshtein.distance(text1, text2)
        return 1.0 - (distance / max_len)

    def _calculate_center_distance(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """计算两个边界框中心点的欧氏距离"""
        center1_x = bbox1.x + bbox1.width / 2
        center1_y = bbox1.y + bbox1.height / 2
        center2_x = bbox2.x + bbox2.width / 2
        center2_y = bbox2.y + bbox2.height / 2

        return ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
```

#### 5.1.3 改进的融合算法

```python
async def _merge_results_improved(
    self,
    mineru_regions: List[Dict],
    multimodal_regions: List[MultimodalOCRRegion]
) -> List[HybridTextRegion]:
    """
    改进的融合算法：MinerU坐标 + 多模态样式

    去重策略：
    1. 以MinerU结果为主（精确坐标）
    2. 为每个MinerU区域匹配多模态样式
    3. 使用严格去重检测
    """
    deduplicator = TextDeduplicator(
        iou_threshold=0.3,           # 30%重叠即认为重复
        text_similarity_threshold=0.85,  # 85%文字相似度
        distance_threshold=50.0      # 50像素距离
    )

    merged = []

    # 第一阶段：处理MinerU文字（精确坐标）
    for idx, mineru_text in enumerate(mineru_regions):
        # 转换bbox格式
        bbox = mineru_text.get("bbox", [])
        if len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        bbox_dict = BoundingBox(
            x=x1,
            y=y1,
            width=x2 - x1,
            height=y2 - y1
        )

        # 构建临时区域用于去重检测
        temp_region = HybridTextRegion(
            id=f"temp_{idx}",
            text=mineru_text.get("txt", ""),
            bbox=bbox_dict,
            confidence=0.95,
            font=None,
            color=None
        )

        # 检查是否与已添加区域重复
        is_dup, matched = deduplicator.is_duplicate(temp_region, merged)
        if is_dup:
            logger.debug(
                "跳过重复的MinerU文字",
                extra={
                    "text": mineru_text.get("txt", ""),
                    "matched_text": matched.text if matched else ""
                }
            )
            continue

        # 查找匹配的多模态样式
        matched_style = self._find_matching_style_by_position(
            bbox_dict,
            multimodal_regions
        )

        # 添加融合结果
        region = HybridTextRegion(
            id=f"region_{len(merged) + 1:03d}",
            text=mineru_text.get("txt", ""),     # MinerU文字
            bbox=bbox_dict,                       # MinerU坐标
            confidence=0.95,
            font=matched_style if matched_style else self._get_default_font(),
            color=matched_style.color if matched_style else "#000000",
            source="mineru"
        )
        merged.append(region)

    logger.info(
        "MinerU文字融合完成",
        extra={
            "mineru_count": len(mineru_regions),
            "merged_count": len(merged),
            "duplicates_removed": len(mineru_regions) - len(merged)
        }
    )

    return merged


def _find_matching_style_by_position(
    self,
    bbox: BoundingBox,
    multimodal_regions: List[MultimodalOCRRegion]
) -> Optional[FontInfo]:
    """
    通过位置匹配查找样式信息

    匹配策略：
    1. 计算中心点距离
    2. 距离阈值内的最佳匹配
    3. 要求最小相似度分数
    """
    if not multimodal_regions:
        return None

    best_match = None
    best_score = 0
    distance_threshold = 100  # 100像素

    target_center_x = bbox.x + bbox.width / 2
    target_center_y = bbox.y + bbox.height / 2

    for mm_region in multimodal_regions:
        mm_bbox = mm_region.bbox
        mm_center_x = mm_bbox.x + mm_bbox.width / 2
        mm_center_y = mm_bbox.y + mm_bbox.height / 2

        # 计算中心点距离
        distance = (
            (target_center_x - mm_center_x) ** 2 +
            (target_center_y - mm_center_y) ** 2
        ) ** 0.5

        if distance > distance_threshold:
            continue

        # 计算相似度分数 (距离越近分数越高)
        score = 1.0 - (distance / distance_threshold)

        if score > best_score and score > 0.5:
            best_score = score
            best_match = mm_region.font

    return best_match
```

### 5.2 问题2：MinerU异步API与Celery架构

#### 5.2.1 架构问题分析

> **问题根源**: MinerU API采用异步模式（提交任务 → 轮询状态 → 获取结果），而Celery任务也是异步执行。

**当前方案的问题**：
1. Celery worker在轮询MinerU结果时会阻塞
2. 长时间轮询占用worker资源，影响其他任务处理
3. 轮询超时风险：网络问题可能导致任务失败

**架构示意图**：
```
┌─────────────────────────────────────────────────────────────────────┐
│                     当前方案（存在问题）                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   [Celery Worker]                                                  │
│        │                                                           │
│        │ 1. 提交MinerU任务                                         │
│        ├─────────────────────────────────────────> [MinerU API]    │
│        │                                                           │
│        │ 2. 阻塞轮询状态（占用worker资源）                          │
│        │ <─────────────────────────────────────┤                   │
│        │                                        │                   │
│        │    等待... (可能30-120秒)             │                   │
│        │                                        │                   │
│        │ 3. 获取结果继续处理                    │                   │
│        │ <─────────────────────────────────────┘                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 方案A：Celery回调链式任务（推荐）

**设计思路**：将任务拆分为多个子任务，通过Celery的链式调用实现非阻塞。

**架构示意图**：
```
┌─────────────────────────────────────────────────────────────────────┐
│              方案A：Celery回调链式任务（推荐）                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Task 1: submit_mineru_task                                        │
│        │                                                           │
│        │ 提交MinerU任务，立即返回task_id                            │
│        ├─────────────────────────────────────────> [MinerU API]    │
│        │                                                           │
│        │ 保存task_id到数据库                                        │
│        │                                                           │
│        │ 触发Task 2（带延迟）                                       │
│        ▼                                                           │
│  Task 2: poll_mineru_result                                       │
│        │                                                           │
│        │ 检查数据库中的task状态                                     │
│        │                                                           │
│        │ ┌─────────────────> [已完成] ──> Task 3: process_result  │
│        │ │                                                        │
│        │ └─────────────────> [处理中] ──> 重新调度Task 2（延迟5秒）│
│        │                                                        │
│        │ └─────────────────> [失败/超时] ──> 标记任务失败         │
│        │                                                        │
│  Task 3: process_result                                           │
│        │                                                           │
│        │ 获取完整结果                                               │
│        │ 融合多模态数据                                             │
│        │ 更新数据库                                                 │
│        │ 触发后续任务（文字去除等）                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**代码实现**：

```python
# backend/app/services/tasks/mineru_tasks.py

from celery import chain, shared_task
from celery.schedules import timedelta
import httpx
from typing import Dict, Any

from app.services.tasks.celery_app import celery_app
from app.core.log_utils import get_logger
from app.db.database import AsyncSessionLocal
from app.utils.async_utils import AsyncRunner

logger = get_logger(__name__)


# ============================================================================
# MinerU识别任务链
# ============================================================================

@celery_app.task(
    bind=True,
    queue='image_editing',
    max_retries=3
)
def submit_mineru_task(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    步骤1: 提交MinerU识别任务

    该任务快速完成，不阻塞worker
    """
    logger.info("步骤1: 提交MinerU任务", extra={
        "task_id": task_id,
        "slide_id": slide_id,
        "cos_key": cos_key
    })

    try:
        with AsyncRunner() as runner:
            async def do_submit():
                from app.services.editing.mineru_service import MinerUService
                from app.repositories.image_editing import ImageEditingRepository

                async with AsyncSessionLocal() as db:
                    repo = ImageEditingRepository(db)
                    service = MinerUService(db)

                    # 获取图片URL
                    image_url = service._get_image_url(cos_key)

                    # 提交MinerU任务
                    mineru_task_id = await service.submit_task(
                        image_url=image_url,
                        options={
                            "enable_ocr": True,
                            "enable_formula": True,
                            "enable_table": True
                        }
                    )

                    # 保存MinerU task_id到数据库
                    await repo.update_task_mineru_id(
                        task_id=task_id,
                        mineru_task_id=mineru_task_id
                    )
                    await db.commit()

                    return {
                        "mineru_task_id": mineru_task_id,
                        "status": "submitted"
                    }

            result = runner.run(do_submit())

            # 触发轮询任务（延迟5秒后开始）
            poll_mineru_result.apply_async(
                args=[task_id, slide_id, cos_key, user_id],
                countdown=5,  # 5秒后开始轮询
                queue='image_editing'
            )

            return {
                "task_id": task_id,
                "slide_id": slide_id,
                "cos_key": cos_key,
                "status": "pending",
                "progress": 10,
                "mineru_task_id": result["mineru_task_id"]
            }

    except Exception as exc:
        logger.error("提交MinerU任务失败", extra={
            "task_id": task_id,
            "error": str(exc)
        })
        # 标记任务失败
        _mark_task_as_failed(task_id, slide_id, exc)
        raise


@celery_app.task(
    bind=True,
    queue='image_editing',
    max_retries=30  # 最多轮询30次（5分钟）
)
def poll_mineru_result(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    步骤2: 轮询MinerU任务结果

    根据状态决定下一步：
    - completed: 调用process_result处理结果
    - processing/pending: 重新调度轮询任务（延迟5秒）
    - failed: 标记任务失败
    """
    logger.info("步骤2: 轮询MinerU结果", extra={
        "task_id": task_id,
        "slide_id": slide_id
    })

    try:
        with AsyncRunner() as runner:
            async def do_poll():
                from app.services.editing.mineru_service import MinerUService
                from app.repositories.image_editing import ImageEditingRepository

                async with AsyncSessionLocal() as db:
                    repo = ImageEditingRepository(db)
                    service = MinerUService(db)

                    # 获取MinerU task_id
                    task_record = await repo.get_task_by_id(task_id)
                    mineru_task_id = task_record.mineru_task_id

                    if not mineru_task_id:
                        raise Exception("MinerU task_id not found")

                    # 查询MinerU任务状态
                    status_data = await service.poll_result(mineru_task_id)
                    status = status_data.get("status")

                    logger.info("MinerU任务状态", extra={
                        "task_id": task_id,
                        "mineru_task_id": mineru_task_id,
                        "status": status
                    })

                    return status_data

            status_data = runner.run(do_poll())
            status = status_data.get("status")

            if status == "completed":
                # 处理完成，触发结果处理任务
                process_mineru_result.apply_async(
                    args=[task_id, slide_id, cos_key, user_id],
                    queue='image_editing'
                )

                return {
                    "task_id": task_id,
                    "status": "polling_completed",
                    "progress": 50
                }

            elif status in ["processing", "pending"]:
                # 仍在处理中，重新调度轮询任务
                poll_mineru_result.apply_async(
                    args=[task_id, slide_id, cos_key, user_id],
                    countdown=5,  # 5秒后再次轮询
                    queue='image_editing'
                )

                return {
                    "task_id": task_id,
                    "status": "polling",
                    "progress": 20
                }

            else:  # failed
                raise Exception(f"MinerU task failed: {status_data.get('message')}")

    except Exception as exc:
        logger.error("轮询MinerU结果失败", extra={
            "task_id": task_id,
            "error": str(exc)
        })
        _mark_task_as_failed(task_id, slide_id, exc)
        raise


@celery_app.task(
    bind=True,
    queue='image_editing'
)
def process_mineru_result(
    self,
    task_id: str,
    slide_id: str,
    cos_key: str,
    user_id: str = None
) -> Dict[str, Any]:
    """
    步骤3: 处理MinerU识别结果

    1. 获取完整识别结果
    2. 融合多模态样式数据
    3. 保存到数据库
    4. 触发后续任务（文字去除等）
    """
    logger.info("步骤3: 处理MinerU结果", extra={
        "task_id": task_id,
        "slide_id": slide_id
    })

    try:
        with AsyncRunner() as runner:
            async def do_process():
                from app.services.editing.mineru_multimodal_fusion_service import MinerUMultimodalFusionService
                from app.repositories.image_editing import ImageEditingRepository

                async with AsyncSessionLocal() as db:
                    repo = ImageEditingRepository(db)
                    fusion_service = MinerUMultimodalFusionService(db)

                    # 获取MinerU task_id
                    task_record = await repo.get_task_by_id(task_id)
                    mineru_task_id = task_record.mineru_task_id

                    # 获取识别结果
                    mineru_result = await fusion_service.get_mineru_result(mineru_task_id)

                    # 融合多模态样式
                    fused_result = await fusion_service.fuse_with_multimodal(
                        mineru_result=mineru_result,
                        cos_key=cos_key
                    )

                    # 保存结果
                    await repo.save_recognition_result(
                        task_id=task_id,
                        result=fused_result
                    )
                    await db.commit()

                    # 更新任务进度
                    await repo.update_task_progress(
                        task_id=task_id,
                        progress=70
                    )
                    await db.commit()

                    return fused_result

            result = runner.run(do_process())

            # 触发文字去除任务（如果启用）
            from app.core.config import settings
            if settings.ENABLE_TEXT_REMOVAL:
                remove_text_from_image.apply_async(
                    args=[task_id, slide_id, cos_key, user_id],
                    queue='image_editing'
                )

            return {
                "task_id": task_id,
                "slide_id": slide_id,
                "cos_key": cos_key,
                "status": "completed",
                "progress": 70,
                "text_count": len(result.get("text_regions", [])),
                "image_count": len(result.get("image_regions", []))
            }

    except Exception as exc:
        logger.error("处理MinerU结果失败", extra={
            "task_id": task_id,
            "error": str(exc)
        })
        _mark_task_as_failed(task_id, slide_id, exc)
        raise
```

#### 5.2.3 方案B：数据库状态轮询（备选）

**设计思路**：前端通过轮询API检查任务状态，后端只在数据库更新状态。

**架构示意图**：
```
┌─────────────────────────────────────────────────────────────────────┐
│            方案B：数据库状态轮询（备选方案）                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [前端]                                                            │
│    │                                                               │
│    │ 轮询 GET /api/v1/image_editing/status/{task_id}              │
│    │                                                               │
│  [后端API]                                                         │
│    │                                                               │
│    │ 检查数据库状态                                                │
│    │                                                               │
│    │ ┌─── [pending] ──> 返回"处理中"                               │
│    │ │                                                           │
│    │ ├─── [processing] ──> 检查MinerU状态                          │
│    │ │      │                                                    │
│    │ │      ├─── [完成] ──> 获取结果，保存到数据库                 │
│    │ │      ├─── [处理中] ──> 返回"处理中"                         │
│    │ │      └─── [失败] ──> 标记失败，返回错误                     │
│    │ │                                                           │
│    │ └─── [completed] ──> 返回完整结果                             │
│    │                                                           │
│  [数据库]                                                          │
│    │                                                               │
│    │ 存储任务状态                                                  │
│    │ - pending: 待处理                                             │
│    │ - processing: MinerU处理中                                   │
│    │ - completed: 已完成                                           │
│    │ - failed: 失败                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

**代码实现**：

```python
# backend/app/services/editing/mineru_polling_service.py

from typing import Dict, Any
import httpx
import asyncio
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class MinerUPollingService:
    """
    MinerU轮询服务

    在API请求时检查MinerU任务状态，避免长时间阻塞worker
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_url = settings.MINERU_API_URL
        self.token = settings.MINERU_TOKEN

    async def check_and_update_status(
        self,
        task_id: str,
        mineru_task_id: str
    ) -> Dict[str, Any]:
        """
        检查并更新MinerU任务状态

        由API调用触发，避免后台worker阻塞
        """
        # 查询MinerU状态
        status_data = await self._query_mineru_status(mineru_task_id)
        status = status_data.get("status")

        logger.info("MinerU状态检查", extra={
            "task_id": task_id,
            "mineru_task_id": mineru_task_id,
            "status": status
        })

        if status == "completed":
            # 获取完整结果
            result = await self._fetch_and_save_result(
                task_id,
                mineru_task_id,
                status_data
            )
            return {
                "status": "completed",
                "result": result
            }

        elif status == "failed":
            # 标记失败
            await self._mark_task_failed(
                task_id,
                status_data.get("message", "Unknown error")
            )
            return {
                "status": "failed",
                "error": status_data.get("message")
            }

        else:  # processing, pending
            # 更新进度估算
            progress = self._estimate_progress(status_data)
            await self._update_progress(task_id, progress)

            return {
                "status": "processing",
                "progress": progress
            }

    async def _query_mineru_status(self, mineru_task_id: str) -> Dict:
        """查询MinerU任务状态"""
        status_url = f"{self.api_url}/{mineru_task_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                status_url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                return result.get("data", {})

            raise Exception(f"MinerU API error: {result.get('message')}")

    async def _fetch_and_save_result(
        self,
        task_id: str,
        mineru_task_id: str,
        status_data: Dict
    ) -> Dict:
        """获取并保存完整结果"""
        from app.services.editing.mineru_multimodal_fusion_service import MinerUMultimodalFusionService
        from app.repositories.image_editing import ImageEditingRepository

        fusion_service = MinerUMultimodalFusionService(self.db)
        repo = ImageEditingRepository(self.db)

        # 融合多模态数据
        fused_result = await fusion_service.fuse_with_multimodal(
            mineru_result=status_data.get("content", {}),
            cos_key=repo.get_task_cos_key(task_id)
        )

        # 保存结果
        await repo.save_recognition_result(
            task_id=task_id,
            result=fused_result
        )
        await self.db.commit()

        return fused_result

    def _estimate_progress(self, status_data: Dict) -> int:
        """估算进度"""
        progress = status_data.get("progress", 0)
        # MinerU进度 0-100，映射到我们的进度 10-60
        return 10 + int(progress * 0.5)

    async def _update_progress(self, task_id: str, progress: int):
        """更新任务进度"""
        from app.repositories.image_editing import ImageEditingRepository

        repo = ImageEditingRepository(self.db)
        await repo.update_task_progress(task_id, progress)
        await self.db.commit()

    async def _mark_task_failed(self, task_id: str, error_msg: str):
        """标记任务失败"""
        from app.repositories.image_editing import ImageEditingRepository
        from app.models.image_editing_task import EditingTaskStatus

        repo = ImageEditingRepository(self.db)
        await repo.update_task_status(
            task_id=task_id,
            status=EditingTaskStatus.FAILED,
            error_message=error_msg
        )
        await self.db.commit()
```

**API端点实现**：

```python
# backend/app/api/v1/endpoints/image_editing.py

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取任务状态

    如果MinerU任务正在处理，会检查最新状态
    """
    from app.services.editing.mineru_polling_service import MinerUPollingService
    from app.repositories.image_editing import ImageEditingRepository

    repo = ImageEditingRepository(db)
    task = await repo.get_task_by_id(task_id)

    if not task:
        raise NotFoundException(f"Task {task_id} not found")

    # 如果任务在处理中，检查MinerU状态
    if task.status == EditingTaskStatus.PROCESSING and task.mineru_task_id:
        polling_service = MinerUPollingService(db)
        status_result = await polling_service.check_and_update_status(
            task_id=task_id,
            mineru_task_id=task.mineru_task_id
        )

        if status_result["status"] == "completed":
            # 重新获取任务数据
            task = await repo.get_task_by_id(task_id)

    return StandardResponse(data={
        "task_id": task_id,
        "status": task.status.value,
        "progress": task.progress,
        "recognition_result": task.recognition_result,
        "edited_image": task.edited_image
    })
```

#### 5.2.4 方案对比

| 方面 | 方案A: Celery回调链 | 方案B: 数据库轮询 |
|------|---------------------|-------------------|
| **Worker资源占用** | 低（快速释放） | 中（每次API请求占用） |
| **实现复杂度** | 中 | 低 |
| **状态实时性** | 中（依赖轮询间隔） | 高（前端主动查询） |
| **扩展性** | 高（易于添加新步骤） | 中 |
| **容错性** | 高（自动重试） | 中（依赖前端重试） |
| **推荐场景** | 后台处理、大批量任务 | 交互式任务、需要实时反馈 |

**推荐选择**：
- **生产环境**：方案A（Celery回调链）- 稳定可靠，适合批处理
- **开发/测试**：方案B（数据库轮询）- 简单快速，便于调试

---

## 6. 基于现有架构的实现方案

### 6.1 文件组织结构变更

```
backend/app/
├── api/v1/endpoints/
│   └── image_editing.py          # 🔧 修改：添加MinerU相关端点
│
├── services/
│   ├── editing/
│   │   ├── image_editing_service.py        # 🔧 修改：添加MinerU支持
│   │   ├── text_removal_service.py         # ✅ 保持不变
│   │   └── mineru_multimodal_fusion_service.py  # ⭐ 新增：MinerU+多模态融合服务
│   │
│   └── ocr/
│       ├── tencent_ocr_engine.py           # ✅ 保留：腾讯OCR
│       ├── baidu_ocr_engine.py             # ✅ 保留：百度OCR
│       ├── multimodal_ocr_engine.py        # ✅ 保留：多模态OCR
│       ├── hybrid_ocr_fusion.py            # ✅ 保留：混合融合
│       └── mineru_adapter.py               # ⭐ 新增：MinerU适配器
│
├── schemas/
│   └── image_editing.py          # 🔧 修改：添加MinerU相关Schema
│
└── core/
    └── config.py                 # 🔧 修改：添加OCR引擎配置

frontend/src/
├── types/
│   └── imageEditing.ts           # 🔧 修改：添加装饰元素类型
│
├── services/
│   └── imageEditingService.ts    # 🔧 修改：添加MinerU调用
│
├── utils/
│   ├── imageEditingUtils.ts      # 🔧 修改：添加装饰元素处理
│   ├── coordinateConverter.ts    # ⭐ 新增：坐标转换工具
│   └── ocrElementInsert.ts       # 🔧 修改：支持装饰元素插入
│
└── views/Editor/
    └── CanvasTool/
        └── index.vue             # 🔧 修改：添加识别引擎选择
```

### 5.2 新增文件详细说明

#### 5.2.1 MinerU+多模态融合服务

> **说明**: 由于MinerU不提供样式信息，需要与多模态大模型融合

**文件**: `backend/app/services/editing/mineru_multimodal_fusion_service.py`

```python
"""
MinerU + 多模态混合识别服务
MinerU提供精确坐标，多模态大模型提供样式信息
"""

from typing import List, Dict, Optional
from datetime import datetime
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ocr.multimodal_ocr_engine import MultimodalOCREngine
from app.models.schemas.image_editing import (
    TextRegion, ImageRegion, FusionRecognitionResult
)


class MinerUMultimodalFusionService:
    """MinerU + 多模态混合识别服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_url = "https://mineru.net/api/v1/extract/task"
        self.token = settings.mineru_token
        self.multimodal_engine = MultimodalOCREngine(db)

    async def recognize_image(
        self,
        image_url: str,
        image_cos_key: str,
        enable_ocr: bool = True,
        enable_formula: bool = True,
        enable_table: bool = True,
        enable_style_recognition: bool = True
    ) -> FusionRecognitionResult:
        """
        使用MinerU + 多模态混合识别

        Args:
            image_url: 待识别图片的URL（用于MinerU）
            image_cos_key: COS存储的图片key（用于多模态识别）
            enable_ocr: 是否开启OCR
            enable_formula: 是否识别公式
            enable_table: 是否识别表格
            enable_style_recognition: 是否启用样式识别（多模态）

        Returns:
            FusionRecognitionResult: 融合识别结果
        """
        start_time = datetime.now()

        # 步骤1: 并行执行MinerU和多模态识别
        mineru_task = self._recognize_with_mineru(
            image_url, enable_ocr, enable_formula, enable_table
        )

        multimodal_task = self._recognize_with_multimodal(
            image_cos_key
        ) if enable_style_recognition else None

        # 等待MinerU完成
        mineru_result = await mineru_task

        # 如果启用样式识别，等待多模态完成
        multimodal_result = None
        if enable_style_recognition and multimodal_task:
            multimodal_result = await multimodal_task

        # 步骤2: 融合结果
        fused_result = self._fuse_results(
            mineru_result,
            multimodal_result
        )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return FusionRecognitionResult(
            text_regions=fused_result["text_regions"],
            image_regions=fused_result["image_regions"],
            metadata={
                "engine": "mineru_multimodal_fusion",
                "mineru_time_ms": mineru_result.get("processing_time_ms", 0),
                "multimodal_time_ms": multimodal_result.get("processing_time_ms", 0) if multimodal_result else 0,
                "total_time_ms": processing_time,
                "recognized_at": datetime.now().isoformat()
            }
        )

    async def _submit_task(
        self,
        image_url: str,
        enable_ocr: bool,
        enable_formula: bool,
        enable_table: bool
    ) -> str:
        """提交识别任务到MinerU API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        request_data = {
            "url": image_url,
            "is_ocr": enable_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"MinerU API error: {result.get('message')}")

            return result["data"]["task_id"]

    async def _poll_result(self, task_id: str) -> Dict:
        """轮询获取识别结果"""
        status_url = f"{self.api_url}/{task_id}"

        max_attempts = 60
        attempt = 0

        async with httpx.AsyncClient() as client:
            while attempt < max_attempts:
                response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    status = data.get("status")

                    if status == "completed":
                        return data
                    elif status == "failed":
                        raise Exception(f"MinerU task failed: {data.get('message')}")

                attempt += 1
                await asyncio.sleep(2)

        raise Exception("MinerU task timeout")

    def _format_result(self, mineru_result: Dict) -> MinerURecognitionResult:
        """格式化MinerU结果为标准格式"""
        content = mineru_result.get("content", {})

        # 处理文字区域
        text_regions = self._format_text_regions(
            content.get("texts", [])
        )

        # 处理装饰元素
        image_regions = self._format_image_regions(
            content.get("images", [])
        )

        return MinerURecognitionResult(
            text_regions=text_regions,
            image_regions=image_regions,
            metadata={
                "engine": "mineru",
                "recognized_at": datetime.now().isoformat()
            }
        )

    def _fuse_text_regions(
        self,
        mineru_texts: List[Dict],
        multimodal_texts: List[Dict]
    ) -> List[TextRegion]:
        """融合文字区域：MinerU坐标 + 多模态样式"""
        regions = []

        for idx, mineru_text in enumerate(mineru_texts):
            # MinerU bbox格式: [x1, y1, x2, y2]
            bbox = mineru_text.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                bbox_dict = {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
            else:
                bbox_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

            # 查找匹配的多模态样式信息
            matched_style = self._find_matching_style(
                bbox_dict,
                multimodal_texts
            )

            # 使用MinerU的文字内容（更准确）
            # 注意：MinerU使用"txt"字段，不是"text"
            region = TextRegion(
                id=f"text_{idx}",
                text=mineru_text.get("txt", ""),
                bbox=bbox_dict,
                confidence=0.95,
                font=matched_style if matched_style else {
                    "size": 16,  # 默认值
                    "family": "Microsoft YaHei",
                    "weight": "normal",
                    "color": "#000000",
                    "align": "left"
                }
            )

            regions.append(region)

        return regions

    def _find_matching_style(
        self,
        bbox: Dict,
        multimodal_texts: List[Dict]
    ) -> Optional[Dict]:
        """通过位置匹配查找对应的样式信息"""
        if not multimodal_texts:
            return None

        best_match = None
        best_score = 0

        for mm_text in multimodal_texts:
            mm_bbox = mm_text.get("bbox", {})
            # 计算中心点距离
            center_x1 = bbox["x"] + bbox["width"] / 2
            center_y1 = bbox["y"] + bbox["height"] / 2
            center_x2 = mm_bbox.get("x", 0) + mm_bbox.get("width", 0) / 2
            center_y2 = mm_bbox.get("y", 0) + mm_bbox.get("height", 0) / 2

            distance = ((center_x1 - center_x2) ** 2 + (center_y1 - center_y2) ** 2) ** 0.5

            # 距离越小得分越高
            score = 1 / (1 + distance / 100)

            if score > best_score and score > 0.7:
                best_score = score
                best_match = mm_text.get("font")

        return best_match

    def _format_image_regions(
        self,
        mineru_images: List[Dict]
    ) -> List[ImageRegion]:
        """格式化图片区域"""
        regions = []

        for idx, image_item in enumerate(mineru_images):
            # MinerU bbox格式: [x1, y1, x2, y2]
            bbox = image_item.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                bbox_dict = {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
            else:
                bbox_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

            region = ImageRegion(
                id=f"image_{idx}",
                type="decoration",  # MinerU不区分类型
                bbox=bbox_dict,
                cos_key=image_item.get("path", ""),  # 注意：MinerU使用"path"字段
                confidence=0.9
            )

            regions.append(region)

        return regions

    # ========== 辅助方法 ==========

    async def _recognize_with_mineru(
        self,
        image_url: str,
        enable_ocr: bool,
        enable_formula: bool,
        enable_table: bool
    ) -> Dict:
        """使用MinerU识别（获取精确坐标）"""
        # 提交任务
        task_id = await self._submit_mineru_task(
            image_url, enable_ocr, enable_formula, enable_table
        )

        # 轮询结果
        result = await self._poll_mineru_result(task_id)

        return {
            "content": result.get("content", {}),
            "task_id": task_id
        }

    async def _recognize_with_multimodal(
        self,
        image_cos_key: str
    ) -> Dict:
        """使用多模态大模型识别（获取样式信息）"""
        return await self.multimodal_engine.recognize_image(image_cos_key)

    def _fuse_results(
        self,
        mineru_result: Dict,
        multimodal_result: Optional[Dict]
    ) -> Dict:
        """融合MinerU和多模态结果"""
        content = mineru_result.get("content", {})

        # 处理文字区域
        text_regions = self._fuse_text_regions(
            content.get("texts", []),
            multimodal_result.get("text_regions", []) if multimodal_result else []
        )

        # 处理图片区域
        # 注意：MinerU使用"imgs"不是"images"
        image_regions = self._format_image_regions(
            content.get("imgs", [])
        )

        return {
            "text_regions": text_regions,
            "image_regions": image_regions
        }

    async def _submit_mineru_task(
        self,
        image_url: str,
        enable_ocr: bool,
        enable_formula: bool,
        enable_table: bool
    ) -> str:
        """提交MinerU任务"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        request_data = {
            "url": image_url,
            "is_ocr": enable_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"MinerU API error: {result.get('message')}")

            return result["data"]["task_id"]

    async def _poll_mineru_result(self, task_id: str) -> Dict:
        """轮询MinerU结果"""
        status_url = f"{self.api_url}/{task_id}"

        max_attempts = 60
        attempt = 0

        async with httpx.AsyncClient() as client:
            while attempt < max_attempts:
                response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    data = result.get("data", {})
                    status = data.get("status")

                    if status == "completed":
                        return data
                    elif status == "failed":
                        raise Exception(f"MinerU task failed: {data.get('message')}")

                attempt += 1
                await asyncio.sleep(2)

        raise Exception("MinerU task timeout")
```

#### 5.2.2 坐标转换工具

**文件**: `frontend/src/utils/coordinateConverter.ts`

```typescript
/**
 * 坐标转换工具
 * 用于将MinerU返回的坐标转换为前端画布坐标
 */

/**
 * MinerU返回的bbox格式
 * [x1, y1, x2, y2] - 左上角和右下角坐标
 */
export interface MinerUBBox {
  x1: number
  y1: number
  x2: number
  y2: number
}

/**
 * 前PPT元素坐标格式
 */
export interface ElementRect {
  left: number
  top: number
  width: number
  height: number
}

/**
 * 图片尺寸
 */
export interface ImageSize {
  width: number
  height: number
}

/**
 * 坐标转换配置
 */
export interface CoordTransformConfig {
  // 原始图片尺寸
  imageSize: ImageSize
  // 画布尺寸
  viewportSize: number
  viewportRatio: number
  // 目标矩形（默认全画布）
  targetRect?: ElementRect
  // object-fit模式
  objectFit?: 'cover' | 'contain'
}

/**
 * 将MinerU的bbox格式转换为PPT元素坐标
 * @param bbox MinerU bbox [x1, y1, x2, y2]
 * @param config 转换配置
 * @returns PPT元素坐标
 */
export function convertMinerUBBoxToElementRect(
  bbox: number[] | MinerUBBox,
  config: CoordTransformConfig
): ElementRect {
  // 解析bbox
  const mineruBox = Array.isArray(bbox)
    ? { x1: bbox[0], y1: bbox[1], x2: bbox[2], y2: bbox[3] }
    : bbox

  // 计算原始尺寸
  const originalWidth = mineruBox.x2 - mineruBox.x1
  const originalHeight = mineruBox.y2 - mineruBox.y1

  // 获取目标矩形
  const targetRect = config.targetRect || {
    left: 0,
    top: 0,
    width: config.viewportSize,
    height: config.viewportSize * config.viewportRatio
  }

  // 执行坐标转换
  const transformed = mapBBoxToTargetRect(
    {
      x: mineruBox.x1,
      y: mineruBox.y1,
      width: originalWidth,
      height: originalHeight
    },
    targetRect,
    config.imageSize,
    config.objectFit || 'cover'
  )

  return {
    left: transformed.left,
    top: transformed.top,
    width: transformed.width,
    height: transformed.height
  }
}

/**
 * 将bbox映射到目标矩形
 * 支持object-fit: cover和contain模式
 */
function mapBBoxToTargetRect(
  bbox: { x: number; y: number; width: number; height: number },
  target: ElementRect,
  srcImage: ImageSize,
  objectFit: 'cover' | 'contain'
): ElementRect {
  const srcW = srcImage.width
  const srcH = srcImage.height
  const dstW = target.width
  const dstH = target.height

  if (srcW <= 0 || srcH <= 0 || dstW <= 0 || dstH <= 0) {
    // fallback: 不做映射
    return {
      left: target.left + bbox.x,
      top: target.top + bbox.y,
      width: bbox.width,
      height: bbox.height
    }
  }

  // 计算缩放比例（object-position: center）
  const scale =
    objectFit === 'cover'
      ? Math.max(dstW / srcW, dstH / srcH)
      : Math.min(dstW / srcW, dstH / srcH)

  const renderedW = srcW * scale
  const renderedH = srcH * scale
  const offsetX = (renderedW - dstW) / 2
  const offsetY = (renderedH - dstH) / 2

  return {
    left: target.left + bbox.x * scale - offsetX,
    top: target.top + bbox.y * scale - offsetY,
    width: bbox.width * scale,
    height: bbox.height * scale
  }
}

/**
 * 批量转换MinerU bbox
 */
export function batchConvertMinerUBBoxes(
  bboxes: (number[] | MinerUBBox)[],
  config: CoordTransformConfig
): ElementRect[] {
  return bboxes.map(bbox => convertMinerUBBoxToElementRect(bbox, config))
}

export default {
  convertMinerUBBoxToElementRect,
  batchConvertMinerUBBoxes,
  mapBBoxToTargetRect
}
```

---

## 6. 坐标处理逻辑详解

### 6.1 坐标系说明

#### 6.1.1 MinerU坐标系

```
MinerU坐标系 (基于原图分辨率)
┌─────────────────────────────┐
│ (0, 0)                     │
│      ┌─────────────┐        │
│      │  Text       │        │
│      │  [x1, y1]   │        │
│      │      [x2, y2]        │
│      └─────────────┘        │
│                             │
│              (width, height)│
└─────────────────────────────┘

特点：
- 原点在左上角
- 坐标单位：像素
- bbox格式：[x1, y1, x2, y2]
- 基于原图分辨率（如1920x1080）
```

#### 6.1.2 前端画布坐标系

```
前端画布坐标系 (基于viewportSize和viewportRatio)
┌─────────────────────────────┐
│ (0, 0)                     │
│      ┌─────────────┐        │
│      │  Element    │        │
│      │  (left, top)│        │
│      │             │        │
│      │    (width, height)   │
│      └─────────────┘        │
│                             │
│      (viewportSize,         │
│       viewportSize * ratio) │
└─────────────────────────────┘

特点：
- 原点在左上角
- 坐标单位：逻辑像素（可缩放）
- 元素格式：{left, top, width, height}
- 基于viewportSize和viewportRatio
```

### 6.2 坐标转换流程图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          MinerU坐标 → 前端坐标转换流程                               │
└─────────────────────────────────────────────────────────────────────────────────────┘

输入: MinerU bbox = [x1, y1, x2, y2]
      原图尺寸 = {width: 1920, height: 1080}
      画布尺寸 = {width: 1280, height: 720}

步骤1: 解析MinerU bbox
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│   [x1, y1, x2, y2]                                                                 │
│        │                                                                           │
│        ▼                                                                           │
│   原始宽度 = x2 - x1                                                               │
│   原始高度 = y2 - y1                                                               │
│   原始左上角 = (x1, y1)                                                            │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

步骤2: 计算缩放比例
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│   画布宽度 / 原图宽度 = 1280 / 1920 = 0.6667 (scaleX)                              │
│   画布高度 / 原图高度 = 720 / 1080 = 0.6667 (scaleY)                               │
│                                                                                     │
│   如果 object-fit = cover:                                                        │
│     scale = max(scaleX, scaleY) = 0.6667                                          │
│                                                                                     │
│   如果 object-fit = contain:                                                      │
│     scale = min(scaleX, scaleY) = 0.6667                                          │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

步骤3: 计算渲染尺寸和偏移
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│   渲染宽度 = 原图宽度 × scale = 1920 × 0.6667 = 1280                               │
│   渲染高度 = 原图高度 × scale = 1080 × 0.6667 = 720                                │
│                                                                                     │
│   偏移X = (渲染宽度 - 画布宽度) / 2 = (1280 - 1280) / 2 = 0                       │
│   偏移Y = (渲染高度 - 画布高度) / 2 = (720 - 720) / 2 = 0                         │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

步骤4: 计算元素坐标
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│   left = 目标矩形.left + 原始左上角.x × scale - 偏移X                             │
│        = 0 + x1 × 0.6667 - 0 = x1 × 0.6667                                        │
│                                                                                     │
│   top = 目标矩形.top + 原始左上角.y × scale - 偏移Y                              │
│       = 0 + y1 × 0.6667 - 0 = y1 × 0.6667                                        │
│                                                                                     │
│   width = 原始宽度 × scale = (x2 - x1) × 0.6667                                   │
│                                                                                     │
│   height = 原始高度 × scale = (y2 - y1) × 0.6667                                  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

输出: ElementRect = {left, top, width, height}
```

### 6.3 坐标对齐验证

**验证方法**：

```typescript
/**
 * 验证坐标转换是否正确
 */
export function validateCoordinateTransform(
  mineruBBox: number[],
  elementRect: ElementRect,
  config: CoordTransformConfig
): { isValid: boolean; error?: string } {
  // 1. 检查bbox格式
  if (mineruBBox.length !== 4) {
    return { isValid: false, error: 'MinerU bbox格式错误，应为[x1, y1, x2, y2]' }
  }

  const [x1, y1, x2, y2] = mineruBBox

  // 2. 检查坐标顺序
  if (x1 >= x2 || y1 >= y2) {
    return { isValid: false, error: 'MinerU bbox坐标顺序错误' }
  }

  // 3. 检查是否超出原图范围
  const { width, height } = config.imageSize
  if (x1 < 0 || y1 < 0 || x2 > width || y2 > height) {
    return { isValid: false, error: 'MinerU bbox超出原图范围' }
  }

  // 4. 检查元素坐标是否在画布范围内
  const canvasWidth = config.viewportSize
  const canvasHeight = config.viewportSize * config.viewportRatio

  if (
    elementRect.left < 0 ||
    elementRect.top < 0 ||
    elementRect.left + elementRect.width > canvasWidth ||
    elementRect.top + elementRect.height > canvasHeight
  ) {
    return { isValid: false, error: '转换后的元素坐标超出画布范围' }
  }

  // 5. 比例一致性检查
  const scaleX = elementRect.width / (x2 - x1)
  const scaleY = elementRect.height / (y2 - y1)

  if (Math.abs(scaleX - scaleY) > 0.01) {
    return { isValid: false, error: 'X和Y缩放比例不一致' }
  }

  return { isValid: true }
}
```

### 6.4 坐标调试工具

```typescript
/**
 * 坐标调试工具
 */
export class CoordinateDebugger {
  private logs: Array<{
    timestamp: number
    mineruBBox: number[]
    elementRect: ElementRect
    config: CoordTransformConfig
    validation: ReturnType<typeof validateCoordinateTransform>
  }> = []

  /**
   * 记录坐标转换过程
   */
  logTransform(
    mineruBBox: number[],
    elementRect: ElementRect,
    config: CoordTransformConfig
  ) {
    const validation = validateCoordinateTransform(mineruBBox, elementRect, config)

    this.logs.push({
      timestamp: Date.now(),
      mineruBBox,
      elementRect,
      config,
      validation
    })

    if (!validation.isValid) {
      console.error('坐标转换错误:', validation.error)
      console.table({
        mineruBBox,
        elementRect,
        imageSize: config.imageSize,
        viewportSize: config.viewportSize,
        viewportRatio: config.viewportRatio
      })
    }
  }

  /**
   * 导出调试日志
   */
  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2)
  }

  /**
   * 清空日志
   */
  clearLogs() {
    this.logs = []
  }

  /**
   * 绘制调试矩形（用于开发调试）
   */
  drawDebugRect(canvas: HTMLCanvasElement, rect: ElementRect, color: string) {
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.strokeRect(rect.left, rect.top, rect.width, rect.height)
  }
}
```

---

## 7. 配置管理方案

### 7.1 配置项定义

**文件**: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # ========== OCR引擎配置 ==========
    # 默认OCR引擎: mineru | hybrid_ocr | tencent_ocr | baidu_ocr
    DEFAULT_OCR_ENGINE: str = "mineru"

    # MinerU配置
    # 注意：API版本是v4
    MINERU_TOKEN: str = Field(default="", env="MINERU_TOKEN")
    MINERU_API_URL: str = "https://mineru.net/api/v4/extract/task"
    MINERU_MODEL_VERSION: str = "vlm"  # vlm 或 pipeline
    MINERU_TIMEOUT: int = 600  # 超时时间（秒）
    MINERU_MAX_RETRIES: int = 3  # 最大重试次数

    # 文字去除配置
    ENABLE_TEXT_REMOVAL: bool = True  # 是否启用文字去除
    TEXT_REMOVAL_MODEL: str = "dall-e-3"  # 文字去除模型

    # 坐标转换配置
    # 注意：前端图片渲染通常使用 object-fit（如 cover），坐标转换必须与前端渲染模式一致。
    DEFAULT_OBJECT_FIT: str = "cover"  # cover | contain
    # ⚠️ 不建议在生产链路中依赖固定默认图片尺寸（如 1920x1080）。
    # 推荐：识别阶段通过下载图片用PIL读取真实尺寸，或从 MinerU 输出的 page_info.width/height 获取。
    DEFAULT_IMAGE_WIDTH: Optional[int] = None
    DEFAULT_IMAGE_HEIGHT: Optional[int] = None

    class Config:
        env_file = ".env"
```

### 7.2 环境变量配置

**文件**: `backend/.env`

```bash
# ========== MinerU配置 ==========
MINERU_TOKEN=your_mineru_token_here
DEFAULT_OCR_ENGINE=mineru

# ========== 文字去除配置 ==========
ENABLE_TEXT_REMOVAL=true
TEXT_REMOVAL_MODEL=dall-e-3

# ========== 坐标转换配置 ==========
DEFAULT_OBJECT_FIT=cover
```

---

## 8. API接口设计

### 8.1 新增端点

| 端点 | 方法 | 功能 | 队列 |
|------|------|------|------|
| `/api/v1/image_editing/parse_with_mineru` | POST | 使用MinerU识别图片 | image_editing |
| `/api/v1/image_editing/parse_with_engine` | POST | 使用指定引擎识别 | image_editing |
| `/api/v1/image_editing/config` | GET | 获取OCR配置 | - |
| `/api/v1/image_editing/config` | PUT | 更新OCR配置 | - |

### 8.2 请求/响应格式

#### 8.2.1 使用MinerU识别

**请求**：
```http
POST /api/v1/image_editing/parse_with_mineru
Content-Type: application/json

{
  "slide_id": "banana_task_xxx_slide_0",
  "cos_key": "ai-generated/ppt/xxx/slide_0.png",
  "options": {
    "enable_ocr": true,
    "enable_formula": true,
    "enable_table": true,
    "remove_text": true
  }
}
```

**响应**：
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "data": {
    "task_id": "edit_20251226_123456_abc123",
    "status": "pending",
    "estimated_time": 10,
    "message": "MinerU识别任务已创建"
  },
  "error": null,
  "timestamp": "2025-12-26T12:34:56Z",
  "request_id": "req_abc123"
}
```

#### 8.2.2 查询任务状态（完成）

**响应**：
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "data": {
    "task_id": "edit_20251226_123456_abc123",
    "slide_id": "banana_task_xxx_slide_0",
    "status": "completed",
    "progress": 100,
    "recognition_result": {
      "engine": "mineru",
      "text_regions": [
        {
          "id": "text_0",
          "text": "人工智能技术发展现状",
          "bbox": {"x": 250, "y": 80, "width": 500, "height": 60},
          "confidence": 0.98,
          "font": {
            "size": 42,
            "family": "Microsoft YaHei",
            "weight": "bold",
            "color": "#1a1a1a",
            "align": "center"
          }
        }
      ],
      "image_regions": [
        {
          "id": "image_0",
          "type": "decoration",
          "bbox": {"x": 100, "y": 200, "width": 150, "height": 150},
          "cos_key": "extracted/deco_001.png",
          "confidence": 0.95
        }
      ],
      "metadata": {
        "engine": "mineru",
        "recognized_at": "2025-12-26T12:35:00Z"
      }
    },
    "edited_image": {
      "original_cos_key": "ai-generated/ppt/xxx/slide_0.png",
      "edited_cos_key": "image-edited/ppt/xxx/slide_0_no_text.png",
      "processing_time_ms": 8000
    }
  },
  "error": null,
  "timestamp": "2025-12-26T12:35:10Z",
  "request_id": "req_xyz789"
}
```

---

## 9. 实施计划

### 9.1 分阶段实施

#### 第一阶段：MinerU集成（2-3周）

**后端开发**：
- [ ] 创建MinerU识别服务
- [ ] 创建MinerU适配器
- [ ] 修改图片编辑服务，添加MinerU支持
- [ ] 添加配置管理功能
- [ ] 更新API端点
- [ ] 编写单元测试

**前端开发**：
- [ ] 创建坐标转换工具
- [ ] 修改图片编辑服务
- [ ] 添加装饰元素类型定义
- [ ] 修改OCR元素插入逻辑
- [ ] 添加识别引擎选择界面
- [ ] 添加坐标调试工具

#### 第二阶段：测试与优化（1-2周）

- [ ] 功能测试
- [ ] 坐标精度验证
- [ ] 性能测试
- [ ] 边界情况处理
- [ ] 错误处理优化

#### 第三阶段：文档与培训（1周）

- [ ] 编写用户文档
- [ ] 编写开发文档
- [ ] 团队培训

### 9.2 验收标准

| 验收项 | 标准 |
|--------|------|
| 坐标精度 | 偏差 < 5px |
| 识别准确率 | 文字识别率 > 95% |
| 装饰元素识别率 | > 90% |
| 处理时间 | < 15秒（单张图片） |
| 用户体验 | 流畅无卡顿 |

---

## 10. 风险与挑战

### 10.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| MinerU API不稳定 | 高 | 中 | 1. 保留原有OCR方案<br>2. 实现重试机制<br>3. 添加降级策略 |
| 坐标转换错误 | 高 | 低 | 1. 充分测试<br>2. 添加调试工具<br>3. 验证机制 |
| API配额限制 | 中 | 中 | 1. 监控使用量<br>2. 缓存结果<br>3. 多账户备用 |

### 10.2 业务风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 用户期望过高 | 中 | 高 | 1. 明确功能边界<br>2. 提供使用说明<br>3. 收集反馈 |
| 成本增加 | 中 | 中 | 1. 优化调用策略<br>2. 缓存结果<br>3. 按需使用 |

---

## 11. 参考资料

### 11.1 MinerU相关

- [MinerU 官方网站](https://mineru.net/)
- [MinerU API 文档](https://mineru.net/apiManage/docs)
- [MinerU 输出文件格式](https://opendatalab.github.io/MinerU/zh/reference/output_files/)
- [MinerU GitHub 仓库](https://github.com/opendatalab/MinerU)

### 11.2 项目相关

- [AIPPT图片编辑功能架构设计](../../AIPPT图片编辑功能/AIPPT图片编辑功能架构设计.md)
- [AIPPT图片编辑功能增强方案](../../AIPPT图片编辑功能/AIPPT图片编辑功能增强方案.md)

---

## 附录A：MinerU API详细说明

> **原始资料**: `docs/arch/AIPPT图片编辑功能/MinerU.pdf`

### A.1 API端点说明

**请求端点**:
- 创建任务: `POST https://mineru.net/api/v4/extract/task`
- 查询任务: `GET https://mineru.net/api/v4/extract/task/{task_id}`

### A.2 认证说明

**Token获取方式**:
1. 访问 [MinerU官网](https://mineru.net/)
2. 注册账号并登录
3. 进入用户中心获取专属Token
4. Token有效期需关注平台提示，过期后需重新获取

**认证格式**:
```http
Authorization: Bearer {token}
```

### A.3 请求参数说明

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `url` | string | 是 | 文件URL | - |
| `model_version` | string | 否 | vlm 或 pipeline | "vlm" |
| `is_ocr` | boolean | 否 | 是否开启OCR | false |
| `enable_formula` | boolean | 否 | 是否识别公式 | true |
| `enable_table` | boolean | 否 | 是否识别表格 | true |
| `language` | string | 否 | 文档语言 | "ch" |
| `page_ranges` | string | 否 | 页码范围 | - |
| `data_id` | string | 否 | 自定义数据ID | - |

### A.4 响应状态说明

**任务状态值**:
- `running`: 处理中
- `done`: 处理完成
- `failed`: 处理失败

**处理中响应示例**:
```json
{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "running",
    "extract_progress": {
      "extracted_pages": 1,
      "total_pages": 2,
      "start_time": "2025-01-20 11:43:20"
    }
  },
  "msg": "ok"
}
```

**处理完成响应示例**:
```json
{
  "code": 0,
  "data": {
    "task_id": "47726b6e-46ca-4bb9-******",
    "state": "done",
    "full_zip_url": "https://cdn-mineru.openxlab.org.cn/pdf/xxx.zip"
  },
  "msg": "ok"
}
```

### A.5 ZIP文件下载

**重要说明**:
- 任务完成后，`full_zip_url` 字段包含ZIP文件下载链接
- ZIP文件包含识别结果，需要下载并解压
- 主要使用 `content_list.json` 文件

---

## 附录B：MinerU输出文件格式说明

> **原始资料**: `docs/arch/AIPPT图片编辑功能/MinerU输出文件格式.pdf`

### B.1 ZIP文件结构

```
{原文件名}.zip
├── content_list.json    # 主要识别结果（我们需要的）
├── model.json           # 模型推理结果
├── middle.json          # 中间处理结果
├── {原文件名}.md        # Markdown 输出
├── images/              # 提取的图片目录
│   ├── xxx.jpg
│   └── ...
└── layout.pdf           # 布局分析可视化
```

### B.2 content_list.json 格式（VLM后端）

```json
[
  {
    "type": "text",
    "text": "人工智能技术发展现状",
    "text_level": 1,
    "bbox": [62, 480, 946, 904],
    "page_idx": 0
  },
  {
    "type": "image",
    "img_path": "images/xxx.jpg",
    "image_caption": ["Fig. 1. Description"],
    "bbox": [62, 480, 946, 904],
    "page_idx": 1
  },
  {
    "type": "equation",
    "img_path": "images/xxx.jpg",
    "text": "$$Q = f(P)$$",
    "text_format": "latex",
    "bbox": [62, 480, 946, 904],
    "page_idx": 2
  }
]
```

### B.3 坐标说明

**坐标格式**: `[x0, y0, x1, y1]`
- 对于 `content_list.json`（官方说明）：bbox **映射在 0-1000 范围**，需要结合真实图片尺寸（优先：后端 PIL 读取；或 `page_info.width/height` 若可用）还原为像素坐标。
- `x0, y0`: 左上角坐标
- `x1, y1`: 右下角坐标
- 原点在页面左上角
- 需要根据实际图片尺寸进行转换

---

## 附录C：坐标转换示例

```typescript
// 示例：MinerU坐标 → 前端坐标
// 注意：若 MinerU 输出为 0-1000 归一化坐标，需要先还原为像素坐标；若已是像素坐标，则跳过该步。

// 输入：MinerU bbox (从content_list.json)
const mineruBBox = [250, 80, 750, 140]  // [x0, y0, x1, y1]，范围0-1000

// 配置
const config = {
  // 原始图片尺寸（实际图片）
  imageSize: { width: 1920, height: 1080 },
  // 画布尺寸
  viewportSize: 1280,
  viewportRatio: 16/9,
  objectFit: 'cover'
}

// 转换步骤：
// 1. （可选）将0-1000归一化坐标转换为实际像素坐标
const actualX0 = (mineruBBox[0] / 1000) * config.imageSize.width
const actualY0 = (mineruBBox[1] / 1000) * config.imageSize.height
const actualX1 = (mineruBBox[2] / 1000) * config.imageSize.width   // 750/1000 * 1920 = 1440
const actualY1 = (mineruBBox[3] / 1000) * config.imageSize.height  // 140/1000 * 1080 = 151.2

// 2. 转换为画布坐标
const elementRect = convertMinerUBBoxToElementRect(
  [actualX0, actualY0, actualX1, actualY1],
  config
)

// 输出
console.log(elementRect)
// {
//   left: 320,       // 480 × (1280/1920)
//   top: 57.6,       // 86.4 × (720/1080)
//   width: 640,      // (1440-480) × (1280/1920)
//   height: 43.2     // (151.2-86.4) × (720/1080)
// }
```

### C.1 坐标转换公式

**MinerU VLM后端坐标范围**: 0-1000

**转换步骤**:
1. 归一化坐标：`coord_normalized = coord / 1000`
2. 实际像素坐标：`coord_actual = coord_normalized × image_size`
3. 画布坐标：`coord_canvas = coord_actual × (canvas_size / image_size)`

**简化公式**:
```typescript
function convertMinerUBBox(
  mineruBBox: number[],      // [x0, y0, x1, y1]，范围0-1000
  imageSize: { width: number, height: number },
  canvasSize: { width: number, height: number }
): { left: number, top: number, width: number, height: number } {
  // 计算缩放比例
  const scaleX = canvasSize.width / imageSize.width
  const scaleY = canvasSize.height / imageSize.height

  // （可选）将0-1000归一化坐标转换为画布坐标（若已是像素坐标则无需 /1000 与 *imageSize）
  const left = (mineruBBox[0] / 1000) * imageSize.width * scaleX
  const top = (mineruBBox[1] / 1000) * imageSize.height * scaleY
  const width = ((mineruBBox[2] - mineruBBox[0]) / 1000) * imageSize.width * scaleX
  const height = ((mineruBBox[3] - mineruBBox[1]) / 1000) * imageSize.height * scaleY

  return { left, top, width, height }
}
```

---

*文档结束*
