# 前端API配置说明

> **更新日期**: 2025-10-28  
> **适用范围**: PPT内容排版优化功能

## 概述

本项目使用 `frontend/src/configs/api.ts` 文件统一管理所有后端API端点配置，确保API地址的集中管理和维护。

---

## API配置文件结构

```typescript
// frontend/src/configs/api.ts

export const API_CONFIG = {
  // 图片管理相关API
  IMAGES: { ... },
  
  // 图片上传相关API
  IMAGE_UPLOAD: { ... },
  
  // 标签管理相关API
  TAGS: { ... },
  
  // AI生成相关API
  GENERATION: { ... },
  
  // 布局优化相关API (新增)
  LAYOUT: {
    // 优化幻灯片布局
    OPTIMIZE: '/api/v1/layout/optimize',
  },
  
  // ...
} as const

export default API_CONFIG
```

---

## 布局优化API配置

### 新增配置项

在 `API_CONFIG` 对象中添加布局优化相关的API端点：

```typescript
// 布局优化相关API
LAYOUT: {
  // 优化幻灯片布局
  OPTIMIZE: '/api/v1/layout/optimize',
},
```

### 使用示例

#### 在服务模块中使用

```typescript
// frontend/src/services/optimization.ts

import { api } from './api';
import API_CONFIG from '@/configs/api';

export async function optimizeSlideLayout(
  slideId: string,
  elements: PPTElement[],
  canvasSize: { width: number; height: number },
  options?: OptimizationRequest['options']
): Promise<OptimizationResponse> {
  try {
    const request = {
      slide_id: slideId,
      elements: simplifiedElements,
      canvas_size: canvasSize,
      options,
    };

    // 使用API_CONFIG配置的端点
    const response = await api.post<OptimizationResponse>(
      API_CONFIG.LAYOUT.OPTIMIZE,  // 统一管理的API端点
      request
    );

    return response.data;
  } catch (error) {
    // 错误处理
  }
}
```

#### 在组件中使用

```typescript
// frontend/src/views/Editor/Toolbar/MagicButton.vue

import API_CONFIG from '@/configs/api';
import { optimizeSlideLayout } from '@/services/optimization';

const handleOptimize = async () => {
  // 调用服务函数（内部使用API_CONFIG）
  const response = await optimizeSlideLayout(
    currentSlide.value.id,
    currentSlide.value.elements,
    canvasSize
  );
  
  // 处理响应
};
```

---

## 配置规范

### 命名规范

1. **模块命名**：使用大写字母和下划线，如 `LAYOUT`、`IMAGES`
2. **端点命名**：使用大写字母和下划线，如 `OPTIMIZE`、`LIST`
3. **动态参数**：使用箭头函数，如 `DETAIL: (id: string) => \`/api/v1/images/\${id}\``

### 路径规范

1. **完整路径**：包含版本号，如 `/api/v1/layout/optimize`
2. **RESTful风格**：遵循RESTful API设计规范
3. **统一前缀**：所有API都以 `/api/v1/` 开头

---

## 优势

### 1. 集中管理
- 所有API端点在一个文件中定义
- 便于统一修改和维护
- 避免硬编码路径散落在各处

### 2. 类型安全
```typescript
// TypeScript会提供自动补全和类型检查
const url = API_CONFIG.LAYOUT.OPTIMIZE;  // 类型安全
const url2 = API_CONFIG.LAYOUT.WRONG;    // 编译错误
```

### 3. 易于重构
```typescript
// 如果API路径变更，只需修改一处
LAYOUT: {
  OPTIMIZE: '/api/v2/layout/optimize',  // 版本升级
},
```

### 4. 便于测试
```typescript
// 在测试环境中可以轻松Mock API配置
jest.mock('@/configs/api', () => ({
  API_CONFIG: {
    LAYOUT: {
      OPTIMIZE: 'http://localhost:3000/mock/layout/optimize',
    },
  },
}));
```

---

## 实施步骤

### 步骤1：更新API配置文件

```bash
# 编辑文件
vim frontend/src/configs/api.ts
```

在文件末尾（`AI_MODELS` 配置之后）添加：

```typescript
  // 布局优化相关API
  LAYOUT: {
    // 优化幻灯片布局
    OPTIMIZE: '/api/v1/layout/optimize',
  },
```

### 步骤2：创建类型定义

```bash
# 创建类型定义文件
touch frontend/src/types/optimization.ts
```

### 步骤3：实现API服务

```bash
# 创建服务文件
touch frontend/src/services/optimization.ts
```

在服务文件中导入并使用 `API_CONFIG`：

```typescript
import API_CONFIG from '@/configs/api';

export async function optimizeSlideLayout(...) {
  const response = await api.post(
    API_CONFIG.LAYOUT.OPTIMIZE,  // 使用配置
    request
  );
}
```

### 步骤4：在组件中使用

```typescript
import { optimizeSlideLayout } from '@/services/optimization';

// 直接调用服务函数，无需关心API路径
const result = await optimizeSlideLayout(slideId, elements, canvasSize);
```

---

## 扩展示例

如果未来需要添加更多布局优化相关的API：

```typescript
// 布局优化相关API
LAYOUT: {
  // 优化幻灯片布局
  OPTIMIZE: '/api/v1/layout/optimize',
  
  // 批量优化（未来扩展）
  BATCH_OPTIMIZE: '/api/v1/layout/batch-optimize',
  
  // 获取优化历史（未来扩展）
  HISTORY: '/api/v1/layout/history',
  
  // 保存优化偏好（未来扩展）
  SAVE_PREFERENCE: '/api/v1/layout/preference',
},
```

---

## 注意事项

### 1. 不要硬编码路径

❌ **错误做法**：
```typescript
// 在服务中硬编码路径
const response = await api.post('/api/v1/layout/optimize', data);
```

✅ **正确做法**：
```typescript
// 使用API_CONFIG
import API_CONFIG from '@/configs/api';
const response = await api.post(API_CONFIG.LAYOUT.OPTIMIZE, data);
```

### 2. 保持配置文件的整洁

- 按功能模块分组
- 添加注释说明
- 保持命名一致性

### 3. 与后端路由保持同步

前端API配置应与后端路由定义保持一致：

```python
# 后端：backend/app/api/v1/router.py
api_router.include_router(
    layout_optimization.router,
    prefix="/layout",
    tags=["布局优化"]
)

# 前端：frontend/src/configs/api.ts
LAYOUT: {
  OPTIMIZE: '/api/v1/layout/optimize',  // 与后端路由一致
}
```

---

## 参考资料

- [架构设计文档-完善版](./架构设计文档-完善版.md)
- [前端项目结构](../../../frontend/README.md)
- [API设计与实现规范](../../standard/API设计与实现规范.md)

---

**文档维护者**: AI开发团队  
**最后更新**: 2025-10-28  
**版本**: v1.0

