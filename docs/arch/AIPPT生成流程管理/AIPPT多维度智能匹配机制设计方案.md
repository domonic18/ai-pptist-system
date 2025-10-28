# AIPPT 多维度智能匹配机制设计方案

## 1. 背景与问题分析

### 1.1 当前架构存在的问题

#### 问题1: 扩展性不足
- **匹配维度单一**: 目前只有语义匹配和布局匹配两个维度
- **硬编码严重**: 匹配维度硬编码在算法中,新增维度需要修改多处代码
- **缺乏统一模型**: 各个匹配器相互独立,没有统一的抽象层

#### 问题2: 算法复杂度高
- **多层嵌套加权**: 存在"加权求和后再加权求和"的嵌套评分结构
  - 布局内部:容量 + layout字段 → 加权求和1
  - 最终评分:布局评分 + 语义评分 → 加权求和2
- **维护困难**: 不同维度的评分标准不一致,难以理解和调试
- **配置分散**: 权重配置与算法逻辑耦合度高

### 1.2 理想架构设计目标

#### 目标1: 统一的多项式模型
```
Score = w1×d1 + w2×d2 + w3×d3 + ... + wn×dn

其中:
- wi: 第i个维度的权重 (可配置)
- di: 第i个维度的评分 (0-1标准化)
- 所有维度平铺,避免嵌套
```

#### 目标2: 高扩展性架构
- **维度即插即用**: 新增维度只需添加评估器和配置权重
- **维度独立计算**: 每个维度完全解耦,支持并行计算
- **配置驱动**: 权重、参数统一配置管理

#### 目标3: 智能降级策略
- **语义缺失降级**: 当后端未返回语义特征时,降级为基础匹配
- **维度缺失兼容**: 其他维度缺失时,只降低该维度权重,不影响整体流程

## 2. 整体架构设计

### 2.1 架构框架图

```
┌─────────────────────────────────────────────────────────────────────┐
│                   多维度智能匹配系统架构                               │
├─────────────────────────────────────────────────────────────────────┤
│  【输入层】Input Layer                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ SlideData    │  │  模板集合     │  │  配置管理     │              │
│  │ (后端JSON)    │  │ (Templates)  │  │ (Configs)    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
├─────────┴──────────────────┴──────────────────┴─────────────────────┤
│  【特征提取层】Feature Extraction Layer                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  语义特征提取器 (Semantic Feature Extractor)                   │   │
│  │  - 从后端JSON提取semanticFeatures (logicType, contentType)   │   │
│  │  - 支持缺失检测和降级触发                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  【维度评估层】Dimension Evaluation Layer (核心层)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ 语义维度     │ │ 容量维度     │ │ 结构维度     │ │ 文字量维度   │  │
│  │ Semantic    │ │ Capacity    │ │ Structure   │ │ TextAmount  │  │
│  │ Dimension   │ │ Dimension   │ │ Dimension   │ │ Dimension   │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ 布局维度     │ │ 视觉维度     │ │ ...更多维度  │                   │
│  │ Layout      │ │ Visual      │ │ (可扩展)     │                   │
│  │ Dimension   │ │ Dimension   │ │             │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
│                                                                      │
│  每个维度评估器:                                                       │
│  - 输入: SlideData + Template                                       │
│  - 输出: 标准化评分 (0-1)                                            │
│  - 独立计算,互不依赖                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  【多项式计算层】Polynomial Calculation Layer                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  统一多项式评分引擎 (Polynomial Scoring Engine)                │   │
│  │                                                               │   │
│  │  Score = Σ(wi × di)                                          │   │
│  │                                                               │   │
│  │  其中:                                                         │   │
│  │  - wi: 第i个维度的权重 (从配置文件加载)                         │   │
│  │  - di: 第i个维度的评分 (由维度评估器计算)                       │   │
│  │  - 单一层级,避免嵌套加权                                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│  【决策选择层】Decision Layer                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ 候选筛选     │ │ 最优选择     │ │ 降级策略     │                   │
│  │ Filter      │ │ Selection   │ │ Fallback    │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
├─────────────────────────────────────────────────────────────────────┤
│  【输出层】Output Layer                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  匹配结果 (Best Template + Score Details)                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

#### 2.2.1 单一职责原则
- **维度评估器**: 每个评估器只负责一个维度的评分计算
- **多项式引擎**: 只负责将各维度评分加权求和
- **配置管理**: 只负责权重和参数的管理

#### 2.2.2 开闭原则
- **对扩展开放**: 新增维度只需添加评估器类,无需修改现有代码
- **对修改封闭**: 现有维度评估器互不依赖,修改一个不影响其他

#### 2.2.3 依赖倒置原则
- **抽象接口**: 所有维度评估器实现统一接口 `DimensionEvaluator`
- **工厂模式**: 通过工厂类动态加载和管理维度评估器

## 3. 数据类型定义


### 3.1 ContentType - 内容类型枚举

**定义**: 基于教育场景的内容类型分类，用于内容语义理解

```typescript
// 内容类型枚举（基于教育场景12种类别的精简分类）
enum ContentType {
  // 教学目标类
  LEARNING_OBJECTIVE = 'learning_objective',     // 学习目标（合并原3种）

  // 课堂引入类
  LESSON_INTRODUCTION = 'lesson_introduction',   // 课堂引入（故事、视频、提问、复习旧知）

  // 问题引导类
  PROBLEM_GUIDANCE = 'problem_guidance',         // 问题引导

  // 概念讲解类
  CONCEPT_EXPLANATION = 'concept_explanation',   // 概念讲解（合并原5种）

  // 案例分析类
  CASE_ANALYSIS = 'case_analysis',               // 案例分析（合并典例分析）

  // 对比分析类
  COMPARISON_ANALYSIS = 'comparison_analysis',   // 对比分析

  // 探究实践类
  INQUIRY_PRACTICE = 'inquiry_practice',         // 探究实践

  // 问题讨论类
  PROBLEM_DISCUSSION = 'problem_discussion',     // 问题讨论（保留原1种）

  // 随堂练习类
  CLASS_EXERCISE = 'class_exercise',             // 随堂练习（合并原2种）

  // 内容总结类
  CONTENT_SUMMARY = 'content_summary',           // 内容总结（合并原4种）

  // 拓展延伸类
  EXTENSION_ENRICHMENT = 'extension_enrichment',  // 拓展延伸

  // 课后作业类
  HOMEWORK_ASSIGNMENT = 'homework_assignment'   // 课后作业（合并原4种）
}
```

### 3.2 LayoutType - 布局类型枚举

**定义**: 基于SmartArt的常用布局类型，用于模板布局标注

```typescript
// 布局类型枚举（精简版 - 基于SmartArt但只保留常用布局）
enum LayoutType {
  // 列表布局类（保留最常用的列表类型）
  VERTICAL_LIST = 'vertical_list',       // 垂直列表（包含基本列表和项目符号列表）
  HORIZONTAL_LIST = 'horizontal_list',   // 水平列表
  MULTI_COLUMN_LIST = 'multi_column_list', // 多列列表

  // 流程布局类（精简后只保留核心流程）
  HORIZONTAL_PROCESS = 'horizontal_process', // 水平流程（基本流程）
  VERTICAL_PROCESS = 'vertical_process',   // 垂直流程
  STEP_PROCESS = 'step_process',         // 步进流程（包含上升和下降）
  ALTERNATING_PROCESS = 'alternating_process', // 交替流程

  // 循环布局类（精简后只保留基本循环）
  BASIC_CYCLE = 'basic_cycle',           // 基本循环（圆形循环）

  // 层次结构布局类（简化的层次布局）
  GENERAL_SPECIFIC = 'general_specific', // 总分布局（总分结构）
  GENERAL_SPECIFIC_GENERAL = 'general_specific_general', // 总分总布局
  TREE_STRUCTURE = 'tree_structure',     // 树形结构

  // 关系布局类（精简合并的关系布局）
  BALANCE = 'balance',                   // 平衡布局（合并平衡关系和平衡）
  FUNNEL = 'funnel',                     // 漏斗图
  INTERSECTING = 'intersecting',         // 相交布局（合并维恩图和相交圆）

  // 矩阵布局类（精简后只保留基本矩阵）
  BASIC_MATRIX = 'basic_matrix',         // 基本矩阵（2x2网格）

  // 棱锥图布局类（简化为常用三角）
  PYRAMID = 'pyramid',                   // 正三角（基本棱锥）
  INVERTED_PYRAMID = 'inverted_pyramid', // 倒三角

  // 图片布局类（简化为最常用的1-2种）
  PICTURE_GRID = 'picture_grid',         // 图片网格（最常用）
  PICTURE_COLLAGE = 'picture_collage',   // 图片拼贴

  // 时间线布局类（简化为最常用的1-2种）
  HORIZONTAL_TIMELINE = 'horizontal_timeline', // 水平时间线
  VERTICAL_TIMELINE = 'vertical_timeline',     // 垂直时间线

  // 其他常见布局
  COMPARISON = 'comparison',             // 对比布局（左右对比）
  PRO_CON = 'pro_con',                   // 优缺点布局
  BEFORE_AFTER = 'before_after',         // 前后对比布局
  SWOT_ANALYSIS = 'swot_analysis',       // SWOT分析布局
  CAUSE_EFFECT = 'cause_effect',         // 因果关系图
  MIND_MAP = 'mind_map'                  // 思维导图
}
```

### 3.3 后端JSON格式设计

#### 3.3.1 标准JSON格式

为了确保前后端接口的统一性和稳定性，后端JSON格式采用固定的数据结构，所有内容类型都使用相同的字段格式：

```typescript
interface AIPPTSlideData {
  type: string
  data: {
    title: string
    semanticFeatures?: {  // 可选字段，支持降级策略
      contentType: ContentType
      layoutType?: LayoutType  // 新增：后端直接推荐布局类型
    }
    items: Array<{
      title: string
      text: string
      metadata: Record<string, any>
    }>
  }
}
```

#### 3.3.2 简化后的JSON结构

**移除 logicType，直接使用 layoutType**：
- 后端语义分析后直接输出推荐的 layoutType
- 避免复杂的逻辑类型映射
- 提高匹配算法的可解释性

**示例**：
```json
{
  "type": "content",
  "data": {
    "title": "分类是第一步",
    "semanticFeatures": {
      "contentType": "concept_explanation",
      "layoutType": "basic_matrix"
    },
    "items": [
      {
        "title": "数轴上有哪些数？",
        "text": "正数、0、负数",
        "metadata": {
          "category": "number_types"
        }
      }
      // ... 其他items
    ]
  }
}
```

#### 3.3.3 具体示例

**问答布局示例：**
```json
{
  "type": "content",
  "data": {
    "title": "脑力大比拼",
    "semanticFeatures": {
      "contentType": "problem_guidance",
      "layoutType": "question_answer"
    },
    "items": [
      {
        "title": "",
        "text": "报出一组数，-5℃和-12℃，或银行账户 +800元 和 -200元。 不画数轴，只用心算，你能立刻判定哪个更大吗？",
        "metadata": {}
      },
      {
        "title": "",
        "text": "想想看，你有什么办法？让我们一起来确定比较有理数大小的法则吧。",
        "metadata": {}
      }
    ]
  }
}
```

**分步布局示例：**
```json
{
  "type": "content",
  "data": {
    "title": "探究建构",
    "semanticFeatures": {
      "contentType": "inquiry_practice",
      "layoutType": "step_by_step"
    },
    "items": [
      {
        "title": "题目",
        "text": "两个负数（-3和-8），应该怎么比较谁大谁小？",
        "metadata": {}
      },
      {
        "title": "第一步：在数轴上找到-3 和 -8",
        "text": "",
        "metadata": {
          "step": 1
        }
      },
      {
        "title": "第二步：观察它们在数轴上的位置",
        "text": " -8 比 -3 更靠左 \n|-8| > |-3| \n所以，-8 < -3",
        "metadata": {
          "step": 2
        }
      },
      {
        "title": "第三步：你观察到了什么规律",
        "text": "两个负数比较大小，绝对值大的反而小",
        "metadata": {
          "step": 3
        }
      }
    ]
  }
}
```

## 4. 匹配维度详细设计

### 4.1 维度分类

| 维度类别 | 维度名称 | 是否必需 | 缺失处理 |
|---------|---------|---------|---------|
| **核心维度** | 布局类型维度 (LayoutType) | 否 | 缺失时跳过,不影响其他维度 |
| **核心维度** | 内容类型维度 (ContentType) | 否 | 缺失时触发整体降级 |
| **核心维度** | 容量维度 (Capacity) | 是 | 必定存在 |
| **核心维度** | 标题结构维度 (TitleStructure) | 是 | 必定存在 |
| **核心维度** | 正文结构维度 (TextStructure) | 是 | 必定存在 |
| **扩展维度** | 文字量维度 (TextAmount) | 是 | 必定存在 |
| **可选维度** | 视觉维度 (Visual) | 否 | 模板无该字段时跳过,不影响其他维度 |

**说明**:
- **核心维度**: 参与基本匹配的维度,内容类型缺失时触发整体降级
- **扩展维度**: 必定存在的扩展匹配维度
- **可选维度**: 根据模板是否标注该字段决定是否参与计算,缺失时不影响其他维度

### 4.2 各维度详细说明

#### 4.2.1 布局类型维度 (LayoutType Dimension)

**定义**: 评估后端推荐的布局类型与模板布局类型的匹配度

**维度说明**:
- **简化架构**: 移除复杂的逻辑类型映射，直接比较 layoutType
- **后端职责**: 语义分析后直接输出推荐的 `layoutType`
- **前端职责**: 直接比较后端和模板的 `layoutType` 是否匹配
- **可解释性**: 匹配逻辑透明，易于调试和理解

**输入数据**:
- `slideData.semanticFeatures.layoutType`: 后端推荐的布局类型（如basic_matrix、vertical_list等）
- `template.slideAnnotation.layoutType`: 模板标注的布局类型

**评分逻辑**:
```typescript
// 直接比较layoutType是否匹配
if (!template.slideAnnotation?.layoutType) {
  评分 = 0.5  // 模板未标注布局类型,中性评分
} else if (template.slideAnnotation.layoutType === slideData.semanticFeatures.layoutType) {
  评分 = 1.0  // 完全匹配
} else {
 评分 = 0.0  // 不匹配
}

// 无嵌套加权,直接返回评分
```

**兼容性考虑**:
- 当 `layoutType` 不匹配时，不影响其他维度的评分
- 该维度权重较低，降低对整体匹配的影响
- 支持降级策略，缺失时跳过该维度

**权重建议**: 0.10 (10%，降低权重)

---

#### 4.2.2 内容类型维度 (ContentType Dimension)

**定义**: 评估内容类型与模板内容类型标注的匹配度

**维度说明**:
- 前端模板**可以标注** `contentType`（表示这页幻灯片适合什么内容类型，如学习目标、案例分析等）
- 后端JSON数据**有** `contentType`（表示内容的语义类型）
- 匹配时：直接比较两者的contentType是否相同

**输入数据**:
- `slideData.semanticFeatures.contentType`: 内容的类型（如learning_objective、case_analysis等）
- `template.slideAnnotation.contentType`: 模板标注的内容类型

**评分逻辑**:
```typescript
// 直接比较contentType
if (!template.slideAnnotation?.contentType) {
  评分 = 0.5  // 模板未标注内容类型,中性评分
} else if (template.slideAnnotation.contentType === slideData.contentType) {
  评分 = 1.0  // 完全匹配
} else {
  评分 = 0.0  // 不匹配
}

// 无嵌套加权,直接返回评分
```

**ContentType枚举示例**:
```typescript
// frontend/src/types/slides.ts
export type ContentType =
  | "learning_objective"      // 学习目标
  | "lesson_introduction"     // 课堂引入
  | "problem_guidance"        // 问题引导
  | "concept_explanation"     // 概念讲解
  | "case_analysis"           // 案例分析
  | "comparison_analysis"     // 对比分析
  | "inquiry_practice"        // 探究实践
  | "problem_discussion"      // 问题讨论
  | "class_exercise"          // 随堂练习
  | "content_summary"         // 内容总结
  | "extension_enrichment"    // 拓展延伸
  | "homework_assignment"     // 课后作业
```

**缺失处理**: 
- 当`semanticFeatures.contentType`缺失时,触发整体降级到基础匹配算法
- 当模板未标注`contentType`时,返回0.5中性评分

**权重建议**: 0.15 (15%)

---

#### 4.2.3 容量维度 (Capacity Dimension)

**定义**: 评估内容项数量与模板容量的适配度

**输入数据**:
- `slideData.items.length`: 内容项数量
- `template.elements`: 模板元素集合(计算容量)

**评分逻辑**:
```typescript
容量利用率 = 内容项数量 / 模板最大容量

评分规则:
- 利用率 = 1.0 (完美匹配): 1.0分
- 利用率 ∈ [0.8, 1.0) (高利用): 0.9分
- 利用率 ∈ [0.6, 0.8) (中等利用): 0.7分
- 利用率 ∈ [0.4, 0.6) (低利用): 0.5分
- 利用率 < 0.4 (过低利用): 0.3分
- 利用率 > 1.0 (超出容量): 0.0分 (硬性过滤)
```

**缺失处理**: 必定存在,无需处理

**权重建议**: 0.25 (25%)

---

#### 4.2.4 标题结构维度 (TitleStructure Dimension)

**定义**: 评估内容项标题数量与模板列表项标题元素数量的匹配度

**匹配对象说明**:
- **模板侧**: 统计`textType="itemTitle"`（列表项标题）的文本元素数量
- **数据侧**: 统计后端JSON中`items`数组里`title`字段非空的item数量
- **不涉及**: 模板的`title`（幻灯片标题）、`subtitle`（副标题）等其他类型

**输入数据**:
- `itemsWithTitle`: 后端JSON中items数组里title字段非空的item数量
- `templateItemTitles`: 模板中`textType="itemTitle"`的元素数量

**评分逻辑**:
```typescript
标题匹配度 = min(itemsWithTitle, templateItemTitles) / max(itemsWithTitle, templateItemTitles)

评分 = 标题匹配度  // 直接返回匹配度,无嵌套加权

特殊情况:
- 如果都为0: 评分 = 1.0 (都没有列表项标题,完美匹配)
- 如果只有模板为0: 评分 = 0.0 (内容有标题但模板没有)
```

**示例**:
```typescript
// 示例1: 完美匹配
模板: 3个itemTitle元素
数据: 3个items有title (例如: [{title: "标题1", text: "..."}, {title: "标题2", text: "..."}, {title: "标题3", text: "..."}])
评分: 3/3 = 1.0

// 示例2: 部分匹配
模板: 3个itemTitle元素  
数据: 1个item有title,2个item只有text (例如: [{title: "标题1", text: "..."}, {text: "..."}, {text: "..."}])
评分: min(1, 3) / max(1, 3) = 1/3 = 0.33

// 示例3: 数量不匹配
模板: 1个itemTitle元素
数据: 3个items有title
评分: min(1, 3) / max(1, 3) = 1/3 = 0.33
```

**缺失处理**: 必定存在,无需处理

**权重建议**: 0.14 (14%)

---

#### 4.2.5 正文结构维度 (TextStructure Dimension)

**定义**: 评估内容项正文数量与模板正文/列表项元素数量的匹配度

**匹配对象说明**:
- **模板侧**: 统计`textType="item"`（列表项目）+ `textType="content"`（正文）的文本元素总数
- **数据侧**: 统计后端JSON中`items`数组里`text`字段非空的item数量（通常所有items都有text）
- **不涉及**: 模板的`title`、`subtitle`、`itemTitle`等其他类型

**输入数据**:
- `itemsWithText`: 后端JSON中items数组里text字段非空的item数量
- `templateTextElements`: 模板中`textType="item"`和`textType="content"`的元素总数

**评分逻辑**:
```typescript
正文匹配度 = min(itemsWithText, templateTextElements) / max(itemsWithText, templateTextElements)

评分 = 正文匹配度  // 直接返回匹配度,无嵌套加权

特殊情况:
- 如果都为0: 评分 = 1.0 (都没有正文,完美匹配)
- 如果只有模板为0: 评分 = 0.0 (内容有正文但模板没有)
```

**示例**:
```typescript
// 示例1: 完美匹配
模板: 3个item元素 + 1个content元素 = 4个文本元素
数据: 4个items有text
评分: 4/4 = 1.0

// 示例2: 您提供的例子A - 完美匹配
模板: 3个itemTitle + 3个item + 1个content
- 标题结构维度: 3个itemTitle vs 3个有title的items → 3/3 = 1.0
- 正文结构维度: (3个item + 1个content) vs 4个有text的items → 4/4 = 1.0
数据: [{title: "标题1", text: "文本1"}, {title: "标题2", text: "文本2"}, {title: "标题3", text: "文本3"}, {text: "文本4"}]

// 示例3: 您提供的例子B - 数量不匹配
模板A: 1个itemTitle + 2个content + 1个item
- 标题结构维度: 1个itemTitle vs 1个有title的items → 1/1 = 1.0
- 正文结构维度: (2个content + 1个item) vs 3个有text的items → 3/3 = 1.0
模板B: 3个itemTitle + 3个item
- 标题结构维度: 3个itemTitle vs 1个有title的items → 1/3 = 0.33 (不匹配!)
- 正文结构维度: 3个item vs 3个有text的items → 3/3 = 1.0
数据: [{title: "标题1", text: "文本1"}, {text: "文本2"}, {text: "文本3"}]
结论: 模板A匹配更好(标题结构+正文结构都是1.0),模板B标题结构不匹配(0.33)
```

**缺失处理**: 必定存在,无需处理

**权重建议**: 0.10 (10%)

---

#### 4.2.6 文字量维度 (TextAmount Dimension)

**定义**: 评估内容文字总量与模板文字容量的匹配度

**输入数据**:
- 内容项文字总数: `totalChars = Σ(title.length + text.length)`
- 模板文字容量估算: 基于模板文本元素的面积和字号估算

**评分逻辑**:
```typescript
文字量比率 = 内容文字总数 / 模板文字容量估算

评分规则:
- 比率 ∈ [0.7, 1.0]: 1.0分
- 比率 ∈ [0.5, 0.7): 0.8分
- 比率 ∈ [0.3, 0.5): 0.6分
- 比率 < 0.3 或 > 1.0: 0.4分
```

**缺失处理**: 必定存在,无需处理

**权重建议**: 0.10 (10%)

---


#### 4.2.7 视觉维度 (Visual Dimension) - 可选维度

**定义**: 评估模板视觉风格与内容主题的匹配度

**维度特点**: 
- 这是一个**可选维度**
- 只有当模板标注了视觉风格字段时才参与计算
- 如果模板未标注,该维度跳过,不影响其他维度计算
- 不会触发整体降级

**输入数据**:
- `slideData.visualStyle`: 视觉风格标签(可选,由后端提供)
- `template.slideAnnotation.visualStyle`: 模板视觉风格标签(可选)

**评分逻辑**:
```typescript
// 1. 检查模板和内容是否都标注了视觉风格
if (!template.slideAnnotation?.visualStyle || !slideData.visualStyle) {
  return null  // 返回null表示该维度不可用,自动跳过
}

// 2. 计算匹配度
if (slideData.visualStyle === template.slideAnnotation.visualStyle) {
  评分 = 1.0  // 完全匹配
} else {
  评分 = 0.5  // 不匹配但给中性分(避免过度惩罚)
}
```

**缺失处理**: 
- 如果`template.slideAnnotation.visualStyle`缺失 → 返回null,该维度跳过
- 如果`slideData.visualStyle`缺失 → 返回null,该维度跳过
- 不影响其他维度的计算和权重分配

**权重建议**: 0.03 (3%)

**使用场景**: 
- 未来当模板库和后端都支持视觉风格标注时启用
- 可以根据主题风格(如商务、教育、创意等)优化匹配
- 目前为预留接口

### 4.3 维度汇总表

| 维度名称 | 英文标识 | 默认权重 | 评分范围 | 计算复杂度 | 维度类型 |
|---------|---------|---------|---------|-----------|---------|
| 布局类型维度 | layoutType | 0.10 | 0.0-1.0 | 低 | 核心维度 |
| 内容类型维度 | contentType | 0.25 | 0.0-1.0 | 低 | 核心维度 |
| 容量维度 | capacity | 0.25 | 0.0-1.0 | 低 | 核心维度 |
| 标题结构维度 | titleStructure | 0.20 | 0.0-1.0 | 低 | 核心维度 |
| 正文结构维度 | textStructure | 0.10 | 0.0-1.0 | 低 | 核心维度 |
| 文字量维度 | textAmount | 0.05 | 0.0-1.0 | 中 | 扩展维度 |
| 视觉维度 | visual | 0.05 | 0.0-1.0 | 低 | 可选维度 |

**权重和**: 1.00 (100%) ✓

**维度类型说明**:
- **核心维度**: 基础匹配维度,其中内容类型缺失时触发整体降级
- **扩展维度**: 必定存在的扩展匹配维度
- **可选维度**: 根据模板是否标注相应字段决定是否参与计算

**权重分配逻辑**:
- **语义匹配 (35%)**: 布局类型10% + 内容类型25%
- **容量匹配 (25%)**: 容量维度
- **结构匹配 (30%)**: 标题结构20% + 正文结构10%
- **其他匹配 (10%)**: 文字量5% + 视觉5%

## 5. 代码架构与文件组织

### 5.1 目录结构设计

```
frontend/src/
├── types/
│   └── slides.ts                           # 扩展ContentType, LayoutType等类型定义
│
├── configs/
│   └── template-matching/                  # 【新增】匹配配置目录
│       ├── dimension-weights.ts            # 维度权重配置
│       └── dimension-registry.ts           # 维度注册表
│
├── utils/
│   └── template-matching/                  # 【新增】匹配算法核心目录
│       ├── types.ts                        # 匹配相关类型定义
│       ├── dimensions/                     # 维度评估器目录
│       │   ├── base-dimension.ts           # 维度评估器基类和接口
│       │   ├── layout-type-dimension.ts    # 布局类型维度评估器
│       │   ├── content-type-dimension.ts   # 内容类型维度评估器
│       │   ├── capacity-dimension.ts       # 容量维度评估器
│       │   ├── title-structure-dimension.ts # 标题结构维度评估器
│       │   ├── text-structure-dimension.ts # 正文结构维度评估器
│       │   ├── text-amount-dimension.ts    # 文字量维度评估器
│       │   └── visual-dimension.ts         # 视觉维度评估器
│       ├── polynomial-engine.ts            # 多项式计算引擎
│       ├── dimension-factory.ts            # 维度工厂(动态加载维度)
│       ├── matching-service.ts             # 匹配服务主入口
│       ├── config-manager.ts               # 配置管理器
│       └── fallback-matcher.ts             # 降级匹配器(基础匹配算法)
│
├── services/
│   └── template-matching-service.ts        # 【新增】模板匹配服务封装
│
└── hooks/
    └── useAIPPT.ts                         # 【修改】集成新的匹配服务
```

### 5.2 核心类设计

#### 5.2.1 维度评估器接口

```typescript
// frontend/src/utils/template-matching/types.ts

/**
 * 维度评估器接口
 * 所有维度评估器必须实现此接口
 */
export interface DimensionEvaluator {
  /**
   * 维度标识符
   */
  readonly id: string

  /**
   * 维度名称
   */
  readonly name: string

  /**
   * 是否必需维度
   */
  readonly required: boolean

  /**
   * 计算该维度的评分
   * @param slideData - 幻灯片数据
   * @param template - 模板
   * @returns 评分 (0-1)，如果维度不可用返回null
   */
  evaluate(slideData: AIPPTSlideData, template: Slide): number | null

  /**
   * 检查该维度是否可用
   * @param slideData - 幻灯片数据
   * @param template - 模板
   * @returns 是否可用
   */
  isAvailable(slideData: AIPPTSlideData, template: Slide): boolean
}

/**
 * 维度评分结果
 */
export interface DimensionScore {
  dimensionId: string
  score: number | null  // null表示维度不可用
  weight: number
  available: boolean
}

/**
 * 模板匹配结果
 */
export interface TemplateMatchResult {
  template: Slide
  totalScore: number
  dimensionScores: DimensionScore[]
  matchedDimensions: string[]  // 参与计算的维度ID列表
}
```

#### 5.2.2 维度评估器基类

```typescript
// frontend/src/utils/template-matching/dimensions/base-dimension.ts

import type { DimensionEvaluator, AIPPTSlideData, Slide } from '../types'

/**
 * 维度评估器抽象基类
 * 提供通用功能，子类只需实现核心评估逻辑
 */
export abstract class BaseDimension implements DimensionEvaluator {
  abstract readonly id: string
  abstract readonly name: string
  abstract readonly required: boolean

  /**
   * 计算评分（模板方法）
   */
  evaluate(slideData: AIPPTSlideData, template: Slide): number | null {
    // 1. 检查维度是否可用
    if (!this.isAvailable(slideData, template)) {
      return null
    }

    // 2. 执行具体评估逻辑
    try {
      const score = this.calculateScore(slideData, template)
      
      // 3. 标准化评分到0-1范围
      return this.normalizeScore(score)
    } catch (error) {
      console.error(`[${this.id}] Evaluation error:`, error)
      return null
    }
  }

  /**
   * 检查维度是否可用（可被子类重写）
   */
  isAvailable(slideData: AIPPTSlideData, template: Slide): boolean {
    return true
  }

  /**
   * 计算原始评分（子类必须实现）
   */
  protected abstract calculateScore(slideData: AIPPTSlideData, template: Slide): number

  /**
   * 标准化评分到0-1范围
   */
  protected normalizeScore(score: number): number {
    return Math.max(0, Math.min(1, score))
  }

  /**
   * 辅助方法：计算模板容量
   */
  protected getTemplateCapacity(template: Slide): number {
    const itemElements = template.elements.filter(el => 
      (el.type === 'text' || el.type === 'shape') && 
      el.textType === 'item' || el.textType === 'itemTitle'
    )
    return Math.max(itemElements.length, 1)
  }

  /**
   * 辅助方法：统计内容项数量
   */
  protected getContentItemCount(slideData: AIPPTSlideData): number {
    return slideData.data.items?.length || 0
  }
}
```

### 5.3 文件内容概览

#### 配置文件

**`frontend/src/configs/template-matching/dimension-weights.ts`**
```typescript
/**
 * 维度权重配置
 * 权重总和必须为1.0
 * 
 * 注意: 所有维度平铺,无嵌套加权
 */
export const DimensionWeights = {
  // 核心维度 (90%)
  layoutType: 0.10,      // 布局类型维度
  contentType: 0.25,     // 内容类型维度
  capacity: 0.25,        // 容量维度
  titleStructure: 0.20,  // 标题结构维度
  textStructure: 0.10,   // 正文结构维度

  // 扩展维度 (10%)
  textAmount: 0.05,      // 文字量维度
  visual: 0.05,          // 视觉维度(可选,模板有visualStyle字段时参与)
}

/**
 * 可选维度列表
 * 这些维度在模板缺失相应字段时会自动跳过
 */
export const OptionalDimensions = ['layoutType', 'visual']

/**
 * 验证权重配置
 */
export function validateWeights(weights: typeof DimensionWeights): boolean {
  const sum = Object.values(weights).reduce((a, b) => a + b, 0)
  const isValid = Math.abs(sum - 1.0) < 0.0001
  
  if (!isValid) {
    console.warn(`权重总和不为1.0: ${sum}`)
  }
  
  return isValid
}
```

**`frontend/src/configs/template-matching/dimension-registry.ts`**
```typescript
import type { DimensionEvaluator } from '@/utils/template-matching/types'

/**
 * 维度注册表
 * 管理所有可用的维度评估器
 */
export interface DimensionRegistryConfig {
  id: string
  evaluatorClass: new () => DimensionEvaluator
  enabled: boolean
  order: number  // 执行顺序
}

export const DimensionRegistry: DimensionRegistryConfig[] = [
  // 核心维度
  {
    id: 'layoutType',
    evaluatorClass: () => import('../utils/template-matching/dimensions/layout-type-dimension').then(m => m.LayoutTypeDimension),
    enabled: true,
    order: 1,
  },
  {
    id: 'contentType',
    evaluatorClass: () => import('../utils/template-matching/dimensions/content-type-dimension').then(m => m.ContentTypeDimension),
    enabled: true,
    order: 2,
  },
  {
    id: 'capacity',
    evaluatorClass: () => import('../utils/template-matching/dimensions/capacity-dimension').then(m => m.CapacityDimension),
    enabled: true,
    order: 3,
  },
  {
    id: 'titleStructure',
    evaluatorClass: () => import('../utils/template-matching/dimensions/title-structure-dimension').then(m => m.TitleStructureDimension),
    enabled: true,
    order: 4,
  },
  {
    id: 'textStructure',
    evaluatorClass: () => import('../utils/template-matching/dimensions/text-structure-dimension').then(m => m.TextStructureDimension),
    enabled: true,
    order: 5,
  },
  {
    id: 'textAmount',
    evaluatorClass: () => import('../utils/template-matching/dimensions/text-amount-dimension').then(m => m.TextAmountDimension),
    enabled: true,
    order: 6,
  },

  // 可选维度 (模板有相应字段时参与计算)
  {
    id: 'visual',
    evaluatorClass: () => import('../utils/template-matching/dimensions/visual-dimension').then(m => m.VisualDimension),
    enabled: true,  // 启用,但模板无visualStyle字段时会自动跳过
    order: 7,
  },
]
```

## 6. 核心功能实现

### 6.1 多项式计算引擎

```typescript
// frontend/src/utils/template-matching/polynomial-engine.ts

import type { DimensionScore, TemplateMatchResult } from './types'
import type { Slide } from '@/types/slides'

/**
 * 多项式计算引擎
 * 负责将各维度评分进行加权求和
 */
export class PolynomialEngine {
  /**
   * 计算模板的总评分
   * 
   * Score = Σ(wi × di)  其中wi为权重，di为维度评分
   * 
   * 支持可选维度自动跳过和权重重新分配:
   * - 当可选维度(如布局、视觉)不可用时,返回null
   * - 系统自动过滤掉null值,只保留可用维度
   * - 对剩余维度的权重进行归一化,确保总和为1.0
   * 
   * @param template - 模板
   * @param dimensionScores - 各维度评分
   * @returns 匹配结果
   */
  calculateScore(
    template: Slide,
    dimensionScores: DimensionScore[]
  ): TemplateMatchResult {
    // 1. 过滤出可用的维度评分(自动跳过返回null的可选维度)
    const availableScores = dimensionScores.filter(ds => 
      ds.available && ds.score !== null
    )

    // 2. 计算可用维度的权重总和(用于归一化)
    const totalWeight = availableScores.reduce((sum, ds) => sum + ds.weight, 0)

    if (totalWeight === 0) {
      // 如果没有可用维度,返回0分
      return {
        template,
        totalScore: 0,
        dimensionScores,
        matchedDimensions: [],
      }
    }

    // 3. 计算加权求和(自动归一化权重)
    let totalScore = 0
    const matchedDimensions: string[] = []

    for (const ds of availableScores) {
      // 归一化权重(确保权重总和为1)
      // 例如: 如果布局维度(0.05)跳过,剩余0.95会被归一化为1.0
      const normalizedWeight = ds.weight / totalWeight
      
      // 加权求和
      totalScore += normalizedWeight * (ds.score || 0)
      
      matchedDimensions.push(ds.dimensionId)
    }

    // 4. 返回结果
    return {
      template,
      totalScore,
      dimensionScores,
      matchedDimensions,
    }
  }

  /**
   * 批量计算多个模板的评分
   */
  calculateBatchScores(
    templates: Slide[],
    getDimensionScores: (template: Slide) => DimensionScore[]
  ): TemplateMatchResult[] {
    return templates.map(template => {
      const dimensionScores = getDimensionScores(template)
      return this.calculateScore(template, dimensionScores)
    })
  }

  /**
   * 选择最优模板
   */
  selectBestMatch(results: TemplateMatchResult[]): TemplateMatchResult | null {
    if (results.length === 0) {
      return null
    }

    // 按总评分降序排序
    const sorted = [...results].sort((a, b) => b.totalScore - a.totalScore)

    return sorted[0]
  }
}
```

### 6.2 维度工厂

```typescript
// frontend/src/utils/template-matching/dimension-factory.ts

import type { DimensionEvaluator } from './types'
import { DimensionRegistry } from '@/configs/template-matching/dimension-registry'
import { DimensionWeights } from '@/configs/template-matching/dimension-weights'

/**
 * 维度工厂
 * 负责动态加载和管理维度评估器实例
 */
export class DimensionFactory {
  private evaluators: Map<string, DimensionEvaluator> = new Map()
  private initialized = false

  /**
   * 初始化所有维度评估器
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return
    }

    // 过滤启用的维度
    const enabledDimensions = DimensionRegistry
      .filter(config => config.enabled)
      .sort((a, b) => a.order - b.order)

    // 动态加载并实例化评估器
    for (const config of enabledDimensions) {
      try {
        const EvaluatorClass = await config.evaluatorClass()
        const evaluator = new EvaluatorClass()
        this.evaluators.set(config.id, evaluator)
        
        console.log(`[DimensionFactory] Loaded dimension: ${config.id}`)
      } catch (error) {
        console.error(`[DimensionFactory] Failed to load dimension: ${config.id}`, error)
      }
    }

    this.initialized = true
  }

  /**
   * 获取所有可用的维度评估器
   */
  getEvaluators(): DimensionEvaluator[] {
    return Array.from(this.evaluators.values())
  }

  /**
   * 获取指定维度的评估器
   */
  getEvaluator(dimensionId: string): DimensionEvaluator | undefined {
    return this.evaluators.get(dimensionId)
  }

  /**
   * 获取维度权重
   */
  getWeight(dimensionId: string): number {
    return DimensionWeights[dimensionId as keyof typeof DimensionWeights] || 0
  }

  /**
   * 获取所有维度ID列表
   */
  getDimensionIds(): string[] {
    return Array.from(this.evaluators.keys())
  }
}
```

### 6.3 匹配服务主入口

```typescript
// frontend/src/utils/template-matching/matching-service.ts

import type { AIPPTSlideData } from '@/types/AIPPT'
import type { Slide } from '@/types/slides'
import type { DimensionScore, TemplateMatchResult } from './types'
import { DimensionFactory } from './dimension-factory'
import { PolynomialEngine } from './polynomial-engine'
import { FallbackMatcher } from './fallback-matcher'

/**
 * 模板匹配服务
 * 整合所有匹配逻辑的主入口
 */
export class TemplateMatchingService {
  private dimensionFactory: DimensionFactory
  private polynomialEngine: PolynomialEngine
  private fallbackMatcher: FallbackMatcher
  private initialized = false

  constructor() {
    this.dimensionFactory = new DimensionFactory()
    this.polynomialEngine = new PolynomialEngine()
    this.fallbackMatcher = new FallbackMatcher()
  }

  /**
   * 初始化服务
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return
    }

    await this.dimensionFactory.initialize()
    this.initialized = true
    
    console.log('[TemplateMatchingService] Initialized')
  }

  /**
   * 查找最佳匹配模板
   * 
   * @param slideData - 幻灯片数据
   * @param availableTemplates - 可用模板列表
   * @returns 最佳匹配的模板
   */
  async findBestMatch(
    slideData: AIPPTSlideData,
    availableTemplates: Slide[]
  ): Promise<Slide> {
    // 确保已初始化
    if (!this.initialized) {
      await this.initialize()
    }

    try {
      // 1. 检查是否需要降级
      if (this.shouldFallback(slideData)) {
        console.log('[TemplateMatchingService] Using fallback matcher')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 2. 筛选候选模板(过滤掉容量不足的)
      const candidates = this.filterCandidates(slideData, availableTemplates)

      if (candidates.length === 0) {
        console.warn('[TemplateMatchingService] No candidates found, using fallback')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 3. 计算各模板的评分
      const results = await this.evaluateTemplates(slideData, candidates)

      // 4. 选择最优模板
      const bestMatch = this.polynomialEngine.selectBestMatch(results)

      if (!bestMatch) {
        console.warn('[TemplateMatchingService] No best match found, using fallback')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 5. 输出匹配详情(调试用)
      this.logMatchResult(bestMatch)

      return bestMatch.template

    } catch (error) {
      console.error('[TemplateMatchingService] Matching failed:', error)
      return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
    }
  }

  /**
   * 判断是否需要降级到基础匹配
   */
  private shouldFallback(slideData: AIPPTSlideData): boolean {
    // 如果没有语义特征,触发降级
    return !slideData.data.semanticFeatures
  }

  /**
   * 筛选候选模板
   */
  private filterCandidates(
    slideData: AIPPTSlideData,
    templates: Slide[]
  ): Slide[] {
    const itemCount = slideData.data.items?.length || 0

    return templates.filter(template => {
      // 获取容量维度评估器
      const capacityEvaluator = this.dimensionFactory.getEvaluator('capacity')
      
      if (!capacityEvaluator) {
        return true
      }

      // 容量不足的模板直接过滤掉
      const capacityScore = capacityEvaluator.evaluate(slideData, template)
      return capacityScore !== null && capacityScore > 0
    })
  }

  /**
   * 评估所有候选模板
   */
  private async evaluateTemplates(
    slideData: AIPPTSlideData,
    templates: Slide[]
  ): Promise<TemplateMatchResult[]> {
    const evaluators = this.dimensionFactory.getEvaluators()

    const results: TemplateMatchResult[] = []

    for (const template of templates) {
      // 计算各维度评分
      const dimensionScores: DimensionScore[] = []

      for (const evaluator of evaluators) {
        const score = evaluator.evaluate(slideData, template)
        const weight = this.dimensionFactory.getWeight(evaluator.id)
        const available = score !== null

        dimensionScores.push({
          dimensionId: evaluator.id,
          score,
          weight: available ? weight : 0,  // 不可用时权重设为0
          available,
        })
      }

      // 计算总评分
      const result = this.polynomialEngine.calculateScore(template, dimensionScores)
      results.push(result)
    }

    return results
  }

  /**
   * 输出匹配结果详情
   */
  private logMatchResult(result: TemplateMatchResult): void {
    console.log('[TemplateMatchingService] Best match:', {
      templateId: result.template.id,
      totalScore: result.totalScore.toFixed(3),
      matchedDimensions: result.matchedDimensions,
      dimensionScores: result.dimensionScores.map(ds => ({
        dimension: ds.dimensionId,
        score: ds.score?.toFixed(3),
        weight: ds.weight.toFixed(3),
        available: ds.available,
      })),
    })
  }
}

// 导出单例
export const templateMatchingService = new TemplateMatchingService()
```

### 6.4 降级匹配器(基础算法)

```typescript
// frontend/src/utils/template-matching/fallback-matcher.ts

import type { AIPPTSlideData } from '@/types/AIPPT'
import type { Slide } from '@/types/slides'

/**
 * 降级匹配器
 * 当智能匹配不可用时,使用基础的随机匹配算法
 */
export class FallbackMatcher {
  /**
   * 基础匹配算法(降级策略)
   * 基于元素数量进行简单匹配和随机选择
   */
  findBasicMatch(
    slideData: AIPPTSlideData,
    availableTemplates: Slide[]
  ): Slide {
    const itemCount = slideData.data.items?.length || 0

    // 1. 筛选容量足够的模板
    const compatibleTemplates = availableTemplates.filter(template => {
      const capacity = this.getTemplateCapacity(template)
      return itemCount <= capacity
    })

    // 2. 如果有兼容模板,随机选择一个
    if (compatibleTemplates.length > 0) {
      const randomIndex = Math.floor(Math.random() * compatibleTemplates.length)
      return compatibleTemplates[randomIndex]
    }

    // 3. 如果没有兼容模板,选择容量最大的模板
    const maxCapacityTemplate = availableTemplates.reduce((max, template) => {
      const templateCapacity = this.getTemplateCapacity(template)
      const maxCapacity = this.getTemplateCapacity(max)
      return templateCapacity > maxCapacity ? template : max
    })

    return maxCapacityTemplate
  }

  /**
   * 获取模板容量
   */
  private getTemplateCapacity(template: Slide): number {
    const itemElements = template.elements.filter(el => 
      (el.type === 'text' || (el.type === 'shape' && el.text)) &&
      (el.textType === 'item' || el.textType === 'itemTitle')
    )
    
    return Math.max(itemElements.length, 1)
  }
}
```

## 7. 维度评估器实现示例

### 7.1 布局类型维度评估器

```typescript
// frontend/src/utils/template-matching/dimensions/layout-type-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'
import type { LayoutType } from '@/types/slides'

/**
 * 布局类型维度评估器
 * 直接评估后端推荐的layoutType与模板layoutType的匹配度
 *
 * 特点: 直接比较，无需复杂的映射转换
 */
export class LayoutTypeDimension extends BaseDimension {
  readonly id = 'layoutType'
  readonly name = '布局类型维度'
  readonly required = false

  /**
   * 检查布局类型特征是否可用
   */
  isAvailable(slideData: AIPPTSlideData, template: Slide): boolean {
    return !!(
      slideData.data.semanticFeatures &&
      slideData.data.semanticFeatures.layoutType
    )
  }

  /**
   * 计算布局类型匹配评分
   *
   * 匹配流程:
   * 1. 获取后端推荐的layoutType
   * 2. 获取模板标注的layoutType
   * 3. 直接比较两个layoutType是否相同
   *
   * 评分逻辑:
   * - 完全匹配: 1.0
   * - 不匹配: 0.0
   * - 后端未推荐或模板未标注: 0.5 (中性分)
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    // 1. 获取后端推荐的layoutType
    const recommendedLayoutType = slideData.data.semanticFeatures!.layoutType as LayoutType

    // 2. 获取模板标注的layoutType
    const templateLayoutType = template.slideAnnotation?.layoutType as LayoutType

    if (!recommendedLayoutType || !templateLayoutType) {
      // 任一缺失布局类型标注,返回中性分
      return 0.5
    }

    // 3. 直接比较两个layoutType是否相同
    return recommendedLayoutType === templateLayoutType ? 1.0 : 0.0
  }
}
```

### 7.2 内容类型维度评估器

```typescript
// frontend/src/utils/template-matching/dimensions/content-type-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

/**
 * 内容类型维度评估器
 * 评估内容类型与模板内容类型标注的匹配度
 * 
 * 特点: 无嵌套加权,直接比较contentType,返回0或1或0.5
 */
export class ContentTypeDimension extends BaseDimension {
  readonly id = 'contentType'
  readonly name = '内容类型维度'
  readonly required = false

  /**
   * 检查内容类型特征是否可用
   */
  isAvailable(slideData: AIPPTSlideData, template: Slide): boolean {
    return !!(
      slideData.data.semanticFeatures &&
      slideData.data.semanticFeatures.contentType
    )
  }

  /**
   * 计算内容类型匹配评分
   * 
   * 匹配流程:
   * 1. 获取后端的contentType
   * 2. 获取模板标注的contentType
   * 3. 直接比较两者是否相同
   * 
   * 评分逻辑:
   * - 完全匹配: 1.0
   * - 不匹配: 0.0
   * - 无模板标注: 0.5 (中性分)
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    // 1. 获取后端JSON数据的contentType
    const dataContentType = slideData.data.semanticFeatures!.contentType
    
    // 2. 获取模板标注的contentType
    const templateContentType = template.slideAnnotation?.contentType

    if (!templateContentType) {
      // 模板没有标注内容类型,返回中性分
      return 0.5
    }

    // 3. 直接比较两者的contentType是否相同
    if (templateContentType === dataContentType) {
      return 1.0  // 完全匹配
    }

    return 0.0  // 不匹配
  }
}
```

### 7.3 容量维度评估器

```typescript
// frontend/src/utils/template-matching/dimensions/capacity-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

/**
 * 容量维度评估器
 * 评估内容项数量与模板容量的匹配度
 */
export class CapacityDimension extends BaseDimension {
  readonly id = 'capacity'
  readonly name = '容量维度'
  readonly required = true

  /**
   * 计算容量匹配评分
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    const itemCount = this.getContentItemCount(slideData)
    const capacity = this.getTemplateCapacity(template)

    // 超出容量,直接返回0分(硬性过滤)
    if (itemCount > capacity) {
      return 0.0
    }

    // 计算容量利用率
    const utilizationRate = itemCount / capacity

    // 根据利用率区间返回评分
    if (Math.abs(utilizationRate - 1.0) < 0.01) {
      return 1.0  // 完美匹配 (利用率=1.0)
    } else if (utilizationRate >= 0.8) {
      return 0.9  // 高利用率 [0.8, 1.0)
    } else if (utilizationRate >= 0.6) {
      return 0.7  // 中等利用率 [0.6, 0.8)
    } else if (utilizationRate >= 0.4) {
      return 0.5  // 低利用率 [0.4, 0.6)
    } else {
      return 0.3  // 过低利用率 < 0.4
    }
  }
}
```

### 7.4 标题结构维度评估器

```typescript
// frontend/src/utils/template-matching/dimensions/title-structure-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

/**
 * 标题结构维度评估器
 * 评估内容项标题数量与模板标题元素数量的匹配度
 * 
 * 特点: 无嵌套加权,直接返回匹配度值
 */
export class TitleStructureDimension extends BaseDimension {
  readonly id = 'titleStructure'
  readonly name = '标题结构维度'
  readonly required = true

  /**
   * 计算标题结构匹配评分
   * 
   * 匹配逻辑:
   * - 模板侧: 统计textType="itemTitle"（列表项标题）的元素数量
   * - 数据侧: 统计items数组中title字段非空的item数量
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    // 1. 统计内容项中有title的item数量（title字段非空）
    const itemsWithTitle = slideData.data.items?.filter(item => item.title && item.title.trim()).length || 0

    // 2. 统计模板中itemTitle类型的元素数量（列表项标题）
    const templateItemTitles = template.elements.filter(el => {
      // 文本元素或带文本的形状元素
      if (el.type === 'text') {
        return el.textType === 'itemTitle'
      }
      if (el.type === 'shape' && el.text) {
        return el.text.type === 'itemTitle'
      }
      return false
    }).length

    // 3. 计算匹配度
    if (itemsWithTitle === 0 && templateItemTitles === 0) {
      return 1.0  // 都没有列表项标题,完美匹配
    }

    if (templateItemTitles === 0) {
      return 0.0  // 内容有标题但模板没有itemTitle元素,不匹配
    }

    // 使用min/max计算匹配度（单一比率，无嵌套加权）
    const matchRatio = Math.min(itemsWithTitle, templateItemTitles) / Math.max(itemsWithTitle, templateItemTitles)
    
    return matchRatio
  }
}
```

### 7.5 正文结构维度评估器

```typescript
// frontend/src/utils/template-matching/dimensions/text-structure-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

/**
 * 正文结构维度评估器
 * 评估内容项正文数量与模板正文元素数量的匹配度
 * 
 * 特点: 无嵌套加权,直接返回匹配度值
 */
export class TextStructureDimension extends BaseDimension {
  readonly id = 'textStructure'
  readonly name = '正文结构维度'
  readonly required = true

  /**
   * 计算正文结构匹配评分
   * 
   * 匹配逻辑:
   * - 模板侧: 统计textType="item"（列表项目）+ textType="content"（正文）的元素总数
   * - 数据侧: 统计items数组中text字段非空的item数量（通常所有items都有text）
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    // 1. 统计内容项中有text的item数量（text字段非空）
    const itemsWithText = slideData.data.items?.filter(item => item.text && item.text.trim()).length || 0

    // 2. 统计模板中item和content类型的元素总数（列表项目+正文）
    const templateTextElements = template.elements.filter(el => {
      // 文本元素或带文本的形状元素
      if (el.type === 'text') {
        return el.textType === 'item' || el.textType === 'content'
      }
      if (el.type === 'shape' && el.text) {
        return el.text.type === 'item' || el.text.type === 'content'
      }
      return false
    }).length

    // 3. 计算匹配度
    if (itemsWithText === 0 && templateTextElements === 0) {
      return 1.0  // 都没有正文内容,完美匹配
    }

    if (templateTextElements === 0) {
      return 0.0  // 内容有正文但模板没有item/content元素,不匹配
    }

    // 使用min/max计算匹配度（单一比率，无嵌套加权）
    const matchRatio = Math.min(itemsWithText, templateTextElements) / Math.max(itemsWithText, templateTextElements)
    
    return matchRatio
  }
}
```

### 7.6 视觉维度评估器(可选维度示例)

```typescript
// frontend/src/utils/template-matching/dimensions/visual-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

/**
 * 视觉维度评估器(可选维度示例)
 * 评估模板视觉风格与内容主题的匹配度
 *
 * 特点: 这是一个可选维度
 * - 模板和内容都有visualStyle字段时才参与计算
 * - 任一缺失时返回null,自动跳过
 * - 不影响其他维度的计算
 */
export class VisualDimension extends BaseDimension {
  readonly id = 'visual'
  readonly name = '视觉维度'
  readonly required = false

  /**
   * 检查视觉维度是否可用
   * 这是可选维度的关键检查点
   */
  isAvailable(slideData: AIPPTSlideData, template: Slide): boolean {
    // 1. 检查模板是否标注了视觉风格(关键!)
    if (!template.slideAnnotation?.visualStyle) {
      return false  // 模板没有视觉风格标注,该维度不可用
    }

    // 2. 检查内容是否有视觉风格标签
    if (!slideData.visualStyle) {
      return false  // 内容没有视觉风格标签,该维度不可用
    }

    return true
  }

  /**
   * 计算视觉风格匹配评分
   */
  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    const contentStyle = slideData.visualStyle!
    const templateStyle = template.slideAnnotation!.visualStyle

    // 精确匹配
    if (contentStyle === templateStyle) {
      return 1.0  // 完全匹配
    }

    // 不匹配但给中性分(避免过度惩罚)
    return 0.5
  }
}
```

## 8. 降级策略详细设计

### 8.1 降级触发条件

| 场景 | 触发条件 | 降级行为 | 影响范围 |
|-----|---------|---------|---------|
| **语义特征缺失** | `semanticFeatures` 字段不存在或无效 | 整体降级到基础匹配算法 | 全局 |
| **可选维度不可用** | 模板缺少可选维度字段(如layoutType、visualStyle) | 该维度返回null,自动跳过,权重重新分配 | 单个维度 |
| **匹配失败** | 所有模板评分都为0 | 降级到基础匹配算法 | 全局 |
| **系统异常** | 匹配过程抛出异常 | 降级到基础匹配算法 | 全局 |

**可选维度处理机制**:
- 布局维度: 模板无`slideAnnotation.layoutType` → 返回null → 该维度跳过
- 视觉维度: 模板无`slideAnnotation.visualStyle`或内容无`visualStyle` → 返回null → 该维度跳过

**权重重新分配**:
当可选维度跳过时,系统会自动重新归一化剩余维度的权重,确保权重总和为1.0。

例如:
- 原始配置: 核心维度92% + 布局5% + 视觉3% = 100%
- 布局维度跳过: 核心维度92% + 视觉3% = 95% → 归一化为100% (各维度×100/95)
- 布局和视觉都跳过: 核心维度92% → 归一化为100% (各维度×100/92)

### 8.2 降级策略流程图

```
┌─────────────────────────────────────┐
│  开始匹配                             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  检查语义特征是否存在                  │
│  (semanticFeatures)                 │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
    存在             缺失
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│ 智能匹配流程 │  │ 基础匹配算法 │
└──────┬──────┘  └─────────────┘
       │               │
       ▼               │
┌─────────────────────┐│
│ 加载维度评估器       ││
└──────┬──────────────┘│
       │               │
       ▼               │
┌─────────────────────┐│
│ 遍历每个模板         ││
└──────┬──────────────┘│
       │               │
       ▼               │
┌─────────────────────┐│
│ 计算各维度评分       ││
│ (维度不可用→权重=0) ││
└──────┬──────────────┘│
       │               │
       ▼               │
┌─────────────────────┐│
│ 多项式加权求和       ││
└──────┬──────────────┘│
       │               │
       ▼               │
┌─────────────────────┐│
│ 是否有有效候选?     ││
└──────┬──────────────┘│
       │               │
   ┌───┴───┐           │
   │       │           │
  是      否           │
   │       │           │
   │       └───────────┘
   │               │
   ▼               ▼
┌─────────────┐  ┌─────────────┐
│ 选择最优模板 │  │ 基础匹配算法 │
└─────────────┘  └─────────────┘
       │               │
       └───────┬───────┘
               │
               ▼
┌─────────────────────────────────────┐
│  返回最终模板                         │
└─────────────────────────────────────┘
```

### 8.3 降级策略代码实现

```typescript
// frontend/src/utils/template-matching/matching-service.ts (扩展版)

export class TemplateMatchingService {
  // ... 其他代码 ...

  /**
   * 智能匹配主流程(支持降级)
   */
  async findBestMatch(
    slideData: AIPPTSlideData,
    availableTemplates: Slide[]
  ): Promise<Slide> {
    try {
      // 【降级检查点1】语义特征缺失检查
      if (this.shouldFallback(slideData)) {
        console.log('[TemplateMatchingService] Semantic features missing, fallback to basic matching')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 筛选候选模板
      const candidates = this.filterCandidates(slideData, availableTemplates)

      // 【降级检查点2】没有候选模板
      if (candidates.length === 0) {
        console.warn('[TemplateMatchingService] No candidates found, fallback to basic matching')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 计算评分
      const results = await this.evaluateTemplates(slideData, candidates)

      // 过滤出有效结果(评分>0)
      const validResults = results.filter(r => r.totalScore > 0)

      // 【降级检查点3】所有模板评分都为0
      if (validResults.length === 0) {
        console.warn('[TemplateMatchingService] All templates scored 0, fallback to basic matching')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      // 选择最优模板
      const bestMatch = this.polynomialEngine.selectBestMatch(validResults)

      if (!bestMatch) {
        console.warn('[TemplateMatchingService] No best match found, fallback to basic matching')
        return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
      }

      this.logMatchResult(bestMatch)
      return bestMatch.template

    } catch (error) {
      // 【降级检查点4】系统异常
      console.error('[TemplateMatchingService] Matching failed with error, fallback to basic matching:', error)
      return this.fallbackMatcher.findBasicMatch(slideData, availableTemplates)
    }
  }

  /**
   * 评估模板时处理维度不可用情况
   */
  private async evaluateTemplates(
    slideData: AIPPTSlideData,
    templates: Slide[]
  ): Promise<TemplateMatchResult[]> {
    const evaluators = this.dimensionFactory.getEvaluators()
    const results: TemplateMatchResult[] = []

    for (const template of templates) {
      const dimensionScores: DimensionScore[] = []

      for (const evaluator of evaluators) {
        try {
          // 计算维度评分
          const score = evaluator.evaluate(slideData, template)
          const baseWeight = this.dimensionFactory.getWeight(evaluator.id)
          
          // 【维度级降级】维度不可用时权重设为0
          const available = score !== null
          const actualWeight = available ? baseWeight : 0

          dimensionScores.push({
            dimensionId: evaluator.id,
            score: score || 0,
            weight: actualWeight,
            available,
          })

          if (!available) {
            console.log(`[TemplateMatchingService] Dimension ${evaluator.id} not available, weight set to 0`)
          }

        } catch (error) {
          // 【维度级降级】维度计算异常,跳过该维度
          console.error(`[TemplateMatchingService] Dimension ${evaluator.id} evaluation failed:`, error)
          dimensionScores.push({
            dimensionId: evaluator.id,
            score: 0,
            weight: 0,
            available: false,
          })
        }
      }

      // 计算总评分
      const result = this.polynomialEngine.calculateScore(template, dimensionScores)
      results.push(result)
    }

    return results
  }
}
```

## 9. 实施计划

### 9.1 分阶段实施策略

#### 第一阶段: 核心框架搭建 (1-2周)

**目标**: 搭建多维度匹配架构的核心框架,实现最小可用版本

**任务清单**:
- [ ] 创建目录结构和文件骨架
- [ ] 实现基础类型定义 (`types.ts`)
- [ ] 实现维度评估器基类 (`base-dimension.ts`)
- [ ] 实现多项式计算引擎 (`polynomial-engine.ts`)
- [ ] 实现维度工厂 (`dimension-factory.ts`)
- [ ] 实现降级匹配器 (`fallback-matcher.ts`)
- [ ] 实现匹配服务主入口 (`matching-service.ts`)
- [ ] 编写单元测试

**交付物**:
- 完整的代码框架
- 核心引擎测试通过
- 技术文档

---

#### 第二阶段: 核心维度实现 (1-2周)

**目标**: 实现核心维度评估器,确保基本匹配能力

**任务清单**:
- [ ] 实现逻辑类型维度评估器 (`logic-type-dimension.ts`)
- [ ] 实现内容类型维度评估器 (`content-type-dimension.ts`)
- [ ] 实现容量维度评估器 (`capacity-dimension.ts`)
- [ ] 实现标题结构维度评估器 (`title-structure-dimension.ts`)
- [ ] 实现正文结构维度评估器 (`text-structure-dimension.ts`)
- [ ] 配置逻辑类型-布局兼容性规则 (`logic-layout-compatibility.ts`)
- [ ] 配置维度权重 (`dimension-weights.ts`)
- [ ] 配置维度注册表 (`dimension-registry.ts`)
- [ ] 集成测试(端到端)
- [ ] 准备测试数据(Mock JSON)

**交付物**:
- 5个核心维度评估器
- 配置文件
- 测试数据和测试报告

---

#### 第三阶段: 扩展维度实现 (1-2周)

**目标**: 实现扩展维度,提升匹配精度

**任务清单**:
- [ ] 实现文字量维度评估器 (`text-amount-dimension.ts`)
- [ ] 实现视觉维度评估器 (`visual-dimension.ts`)
- [ ] 调优权重配置
- [ ] 性能优化
- [ ] 完善日志和监控

**交付物**:
- 扩展维度评估器
- 优化后的权重配置
- 性能测试报告

---

#### 第四阶段: 集成与优化 (1周)

**目标**: 集成到现有系统,优化用户体验

**任务清单**:
- [ ] 集成到 `useAIPPT.ts`
- [ ] 前端UI优化(匹配结果展示)
- [ ] A/B测试对比(新旧算法)
- [ ] 用户反馈收集
- [ ] Bug修复
- [ ] 文档完善

**交付物**:
- 完整集成的系统
- A/B测试报告
- 用户使用文档

### 9.2 风险控制

| 风险类型 | 风险描述 | 应对措施 | 优先级 |
|---------|---------|---------|-------|
| **技术风险** | 新架构性能不达标 | 提前进行性能基准测试,优化算法 | P0 |
| **兼容性风险** | 影响现有功能 | 完善单元测试,保留降级策略 | P0 |
| **数据风险** | 后端数据格式变更 | 与后端约定接口规范,做好版本兼容 | P1 |
| **用户体验风险** | 用户不适应新算法 | A/B测试,收集反馈,逐步切换 | P1 |

### 9.3 验收标准

#### 功能验收
- [ ] 所有维度评估器正常工作
- [ ] 多项式计算引擎评分准确
- [ ] 降级策略正确触发
- [ ] 与现有系统无缝集成

#### 性能验收
- [ ] 单次匹配耗时 < 100ms (P95)
- [ ] 批量匹配(10个模板) < 500ms (P95)
- [ ] 内存占用增长 < 10MB

#### 质量验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过率 100%
- [ ] 代码审查通过
- [ ] 文档完整

## 10. 扩展性说明

### 10.1 如何新增维度

**步骤1**: 创建维度评估器类

```typescript
// frontend/src/utils/template-matching/dimensions/new-dimension.ts

import { BaseDimension } from './base-dimension'
import type { AIPPTSlideData, Slide } from '../types'

export class NewDimension extends BaseDimension {
  readonly id = 'newDimension'
  readonly name = '新维度'
  readonly required = false

  protected calculateScore(slideData: AIPPTSlideData, template: Slide): number {
    // 实现你的评分逻辑
    return 0.5
  }
}
```

**步骤2**: 在权重配置中添加权重

```typescript
// frontend/src/configs/template-matching/dimension-weights.ts

export const DimensionWeights = {
  logicType: 0.22,     // 调整现有权重
  contentType: 0.13,
  capacity: 0.23,
  titleStructure: 0.14,
  textStructure: 0.10,
  textAmount: 0.08,
  newDimension: 0.07,  // 新增维度权重
  visual: 0.03,
}
```

**步骤3**: 在注册表中注册维度

```typescript
// frontend/src/configs/template-matching/dimension-registry.ts

export const DimensionRegistry: DimensionRegistryConfig[] = [
  // ... 现有维度 ...
  {
    id: 'newDimension',
    evaluatorClass: () => import('../utils/template-matching/dimensions/new-dimension').then(m => m.NewDimension),
    enabled: true,
    order: 8,
  },
]
```

**完成!** 新维度会自动参与匹配计算,无需修改其他代码。

### 10.2 如何调整权重

只需修改配置文件:

```typescript
// frontend/src/configs/template-matching/dimension-weights.ts

export const DimensionWeights = {
  // 调整后的权重 (示例)
  logicType: 0.26,       // 增加逻辑类型权重
  contentType: 0.16,     // 增加内容类型权重
  capacity: 0.22,        // 调整容量权重
  titleStructure: 0.14,
  textStructure: 0.10,
  textAmount: 0.09,
  visual: 0.03,
}

// 权重总和 = 1.00 ✓
```

保存后刷新页面即可生效。

**注意**: 调整权重时确保总和为1.0,系统会在运行时验证。

### 10.3 如何禁用维度

在注册表中将 `enabled` 设为 `false`:

```typescript
export const DimensionRegistry: DimensionRegistryConfig[] = [
  // 示例: 如果想临时禁用布局维度
  {
    id: 'layout',
    evaluatorClass: () => import('../utils/template-matching/dimensions/layout-dimension').then(m => m.LayoutDimension),
    enabled: false,  // 禁用布局维度
    order: 7,
  },
  // 或者禁用视觉维度
  {
    id: 'visual',
    evaluatorClass: () => import('../utils/template-matching/dimensions/visual-dimension').then(m => m.VisualDimension),
    enabled: false,  // 禁用视觉维度
    order: 8,
  },
]
```

**注意**: 
- 禁用维度后,该维度完全不参与计算
- 与"可选维度跳过"不同,禁用是在注册阶段就排除了该维度
- 可选维度跳过是在运行时根据模板字段动态决定的

## 11. 总结

### 11.1 方案优势

#### 优势1: 架构清晰,易于扩展
- **单一多项式模型**: 避免多层嵌套加权,逻辑简单明了
- **维度即插即用**: 新增维度只需添加评估器和配置,无需修改现有代码
- **配置驱动**: 权重、参数集中管理,易于调优

#### 优势2: 维护成本低
- **代码解耦**: 各维度评估器独立,互不影响
- **统一接口**: 所有评估器实现相同接口,降低学习成本
- **完善的降级策略**: 确保系统在任何情况下都能正常工作

#### 优势3: 性能优化空间大
- **并行计算**: 维度评估可以并行执行
- **缓存友好**: 模板特征可以预计算和缓存
- **渐进式加载**: 维度评估器按需加载

### 11.2 与现有方案对比

| 对比维度 | 现有方案 | 新方案 |
|---------|---------|--------|
| **匹配维度数量** | 2个(语义+布局) | 7个维度 |
| **算法复杂度** | 多层嵌套加权 | 单一多项式,无嵌套 |
| **扩展性** | 新增维度需修改多处代码 | 新增维度只需添加评估器 |
| **权重管理** | 硬编码在算法中 | 集中配置管理 |
| **可选维度支持** | 不支持 | 支持可选维度,模板无字段时自动跳过 |
| **降级策略** | 简单的缺失检查 | 多级降级,细粒度控制 |
| **代码组织** | 分散在多个文件 | 统一的目录结构 |

**新方案维度分类**:
- **核心维度(6个)**: 逻辑类型(通过映射)、内容类型(直接匹配)、容量、标题结构、正文结构、文字量
- **可选维度(1个)**: 视觉(模板有visualStyle字段时参与)

### 11.3 后续优化方向

1. **机器学习优化**: 基于用户反馈数据,使用机器学习自动调优权重
2. **个性化匹配**: 根据用户偏好调整匹配策略
3. **A/B测试平台**: 支持多种权重配置的在线对比测试
4. **性能监控**: 实时监控匹配性能和准确率
5. **可视化调试**: 提供匹配结果可视化界面,便于调试

---

**文档版本**: v1.0  
**创建日期**: 2025-01-14  
**最后更新**: 2025-01-14  
**作者**: AI Assistant

