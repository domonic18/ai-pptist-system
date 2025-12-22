# AI模型交互统一架构方案

**日期**: 2025-12-21  
**版本**: v2.0（混合方案：按提供商组织）  
**状态**: 待实施  
**更新**: 采用混合方案，按提供商组织Provider，最大化代码复用

---

## 📋 目录

1. [核心设计理念](#核心设计理念)
2. [架构设计](#架构设计)
3. [数据库设计](#数据库设计)
4. [前端设计](#前端设计)
5. [实施方案](#实施方案)

---

## 一、核心设计理念

### 1.1 设计原则

**问题**:
- 当前 `llm/` 和 `imggen/` 架构不一致
- 代码重复，维护成本高
- 扩展困难（新增文生视频等能力）

**目标**:
- ✅ **统一架构**: LLM和ImgGen使用同样的Provider模式
- ✅ **简单清晰**: 没有复杂的推荐引擎，直接配置
- ✅ **易于扩展**: 新增能力或Provider成本低

**核心理念**:

```
统一的AI模型交互架构
├── 能力定义（Capability）
│   ├── chat（对话）
│   ├── vision（多模态）
│   ├── image_gen（文生图）
│   └── video_gen（文生视频，未来）
│
└── Provider实现（按提供商组织）
    ├── base/              # 能力基类定义
    │   ├── chat.py
    │   ├── vision.py
    │   └── image_gen.py
    ├── openai/            # OpenAI相关
    │   ├── client.py      # 共享client
    │   ├── chat.py
    │   ├── vision.py
    │   └── dalle.py
    ├── gemini/            # Gemini相关
    │   ├── client.py
    │   ├── chat.py
    │   ├── vision.py
    │   └── imagen.py
    └── ...（其他提供商）
```

---

## 二、架构设计

### 2.1 目录结构（混合方案）

```
backend/app/core/ai/
├── __init__.py
├── base.py                      # 统一抽象基类
├── models.py                    # 数据模型
├── factory.py                   # Provider工厂
├── registry.py                  # Provider注册
├── tracker.py                   # MLflow追踪（统一）
├── config.py                    # 配置管理
│
└── providers/                   # ⭐ 按提供商组织（混合方案）
    ├── __init__.py
    │
    ├── base/                    # ⭐ 能力基类定义
    │   ├── __init__.py
    │   ├── chat.py              # BaseChatProvider
    │   ├── vision.py            # BaseVisionProvider
    │   ├── image_gen.py         # BaseImageGenProvider
    │   └── video_gen.py         # BaseVideoGenProvider
    │
    ├── openai/                  # ⭐ OpenAI提供商
    │   ├── __init__.py
    │   ├── client.py            # 共享的OpenAI客户端
    │   ├── chat.py              # OpenAI Chat
    │   ├── vision.py            # OpenAI Vision
    │   └── dalle.py             # DALL-E Image
    │
    ├── gemini/                  # ⭐ Gemini提供商
    │   ├── __init__.py
    │   ├── client.py            # 共享的Gemini客户端
    │   ├── chat.py              # Gemini Chat
    │   ├── vision.py            # Gemini Vision
    │   └── imagen.py            # Imagen
    │
    ├── anthropic/               # ⭐ Anthropic提供商
    │   ├── __init__.py
    │   ├── client.py
    │   └── chat.py              # Claude Chat
    │
    ├── qwen/                    # ⭐ 通义千问
    │   ├── __init__.py
    │   ├── client.py
    │   ├── chat.py
    │   └── image.py
    │
    ├── volcengine_ark/          # ⭐ 火山引擎
    │   ├── __init__.py
    │   ├── client.py
    │   └── image.py
    │
    ├── nano_banana/             # ⭐ Nano Banana（仅图片）
    │   ├── __init__.py
    │   └── image.py
    │
    └── openai_compatible/       # ⭐ OpenAI兼容（跨提供商）
        ├── __init__.py
        ├── client.py            # 通用OpenAI兼容客户端
        ├── chat.py              # 支持DeepSeek、智谱等
        └── vision.py
```

**设计说明**:
- ✅ **base/**: 集中管理各能力的基类，统一接口规范
- ✅ **按提供商分组**: 同一提供商的代码在同一目录，便于共享client和错误处理
- ✅ **代码复用**: 同一提供商的多个能力可以共享client、配置、错误处理
- ✅ **清晰内聚**: 每个提供商目录高度内聚，API升级只需修改一个目录
```

### 2.2 核心代码

#### 2.2.1 能力枚举

```python
# ai/models.py

from enum import Enum
from typing import Set

class ModelCapability(str, Enum):
    """模型能力枚举"""
    CHAT = "chat"
    VISION = "vision"
    IMAGE_GEN = "image_gen"
    VIDEO_GEN = "video_gen"
    EMBEDDINGS = "embeddings"
```

#### 2.2.2 统一基类

```python
# ai/base.py

from abc import ABC, abstractmethod
from typing import Set
from .models import ModelCapability

class BaseAIProvider(ABC):
    """所有AI Provider的统一抽象基类"""
    
    def __init__(self, model_config: 'ModelConfig'):
        self.model_config = model_config
        self.tracker = get_tracker()
    
    @abstractmethod
    def get_capabilities(self) -> Set[ModelCapability]:
        """获取支持的能力"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取Provider名称"""
        pass
```

#### 2.2.3 能力基类定义

```python
# ai/providers/base/chat.py

from app.core.ai.base import BaseAIProvider
from app.core.ai.models import ModelCapability

class BaseChatProvider(BaseAIProvider):
    """对话Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        return {ModelCapability.CHAT}
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """对话接口"""
        pass


# ai/providers/base/vision.py

class BaseVisionProvider(BaseAIProvider):
    """多模态Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        return {ModelCapability.VISION}
    
    @abstractmethod
    async def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """多模态对话"""
        pass


# ai/providers/base/image_gen.py

class BaseImageGenProvider(BaseAIProvider):
    """文生图Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        return {ModelCapability.IMAGE_GEN}
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        **kwargs
    ) -> ImageGenerationResult:
        """生成图片"""
        pass


# ai/providers/base/video_gen.py（未来）

class BaseVideoGenProvider(BaseAIProvider):
    """文生视频Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        return {ModelCapability.VIDEO_GEN}
    
    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        **kwargs
    ) -> VideoGenerationResult:
        """生成视频"""
        pass
```

#### 2.2.4 Provider实现示例（展示代码复用）

```python
# ===== OpenAI提供商（展示代码复用） =====

# ai/providers/openai/client.py
class OpenAIClient:
    """OpenAI共享客户端和工具方法"""
    
    def __init__(self, model_config):
        self.client = openai.AsyncOpenAI(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )
        self.model_config = model_config
    
    def handle_error(self, e: Exception):
        """统一错误处理"""
        if isinstance(e, openai.RateLimitError):
            raise RateLimitException("API调用超限")
        elif isinstance(e, openai.AuthenticationError):
            raise AuthenticationException("API密钥无效")
        else:
            raise ProviderException(f"OpenAI错误: {str(e)}")


# ai/providers/openai/chat.py
from ..base.chat import BaseChatProvider
from .client import OpenAIClient

class OpenAIChatProvider(BaseChatProvider, OpenAIClient):
    """OpenAI对话Provider"""
    
    def __init__(self, model_config):
        BaseChatProvider.__init__(self, model_config)
        OpenAIClient.__init__(self, model_config)  # ⭐ 继承共享client
    
    def get_provider_name(self) -> str:
        return "openai"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            self.handle_error(e)  # ⭐ 使用共享的错误处理


# ai/providers/openai/dalle.py
from ..base.image_gen import BaseImageGenProvider
from .client import OpenAIClient

class DALLEProvider(BaseImageGenProvider, OpenAIClient):
    """DALL-E图片生成Provider"""
    
    def __init__(self, model_config):
        BaseImageGenProvider.__init__(self, model_config)
        OpenAIClient.__init__(self, model_config)  # ⭐ 复用同一个client
    
    def get_provider_name(self) -> str:
        return "openai_dalle"
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> ImageGenerationResult:
        try:
            response = await self.client.images.generate(
                model=self.model_config.model_name,
                prompt=prompt,
                size=size,
                quality=quality
            )
            return ImageGenerationResult(
                success=True,
                image_url=response.data[0].url
            )
        except Exception as e:
            self.handle_error(e)  # ⭐ 复用错误处理


# ===== Gemini提供商 =====

# ai/providers/gemini/client.py
class GeminiClient:
    """Gemini共享客户端"""
    
    def __init__(self, model_config):
        self.client = genai.Client(api_key=model_config.api_key)
        self.model_config = model_config
    
    def handle_error(self, e: Exception):
        """统一错误处理"""
        # Gemini特有错误处理
        pass


# ai/providers/gemini/chat.py
from ..base.chat import BaseChatProvider
from .client import GeminiClient

class GeminiChatProvider(BaseChatProvider, GeminiClient):
    """Gemini对话Provider"""
    
    def __init__(self, model_config):
        BaseChatProvider.__init__(self, model_config)
        GeminiClient.__init__(self, model_config)
    
    def get_provider_name(self) -> str:
        return "gemini"
    
    async def chat(self, messages, **kwargs) -> str:
        # Gemini特有实现，复用client
        pass


# ===== OpenAI兼容提供商（跨厂商） =====

# ai/providers/openai_compatible/chat.py
from ..base.chat import BaseChatProvider

class OpenAICompatibleChatProvider(BaseChatProvider):
    """OpenAI兼容对话Provider（支持DeepSeek、智谱等）"""
    
    def __init__(self, model_config):
        super().__init__(model_config)
        self.client = openai.AsyncOpenAI(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )
    
    def get_provider_name(self) -> str:
        return "openai_compatible"
    
    async def chat(self, messages, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_config.model_name,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
```

#### 2.2.5 Provider工厂

```python
# ai/factory.py

from typing import Dict, Type
from .base import BaseAIProvider
from .models import ModelCapability

class AIProviderFactory:
    """AI Provider工厂"""
    
    # Provider注册表: {capability: {provider_name: ProviderClass}}
    _providers: Dict[ModelCapability, Dict[str, Type[BaseAIProvider]]] = {}
    
    @classmethod
    def register(
        cls,
        capability: ModelCapability,
        provider_name: str,
        provider_class: Type[BaseAIProvider]
    ):
        """注册Provider"""
        if capability not in cls._providers:
            cls._providers[capability] = {}
        cls._providers[capability][provider_name] = provider_class
    
    @classmethod
    def create(
        cls,
        model_config: 'ModelConfig',
        capability: ModelCapability
    ) -> BaseAIProvider:
        """创建Provider实例"""
        # 从模型配置获取Provider名称
        provider_name = model_config.provider_mapping.get(capability)
        if not provider_name:
            raise ValueError(f"模型未配置{capability}的Provider")
        
        # 获取Provider类
        if capability not in cls._providers:
            raise ValueError(f"不支持的能力: {capability}")
        
        if provider_name not in cls._providers[capability]:
            raise ValueError(f"未注册的Provider: {capability}/{provider_name}")
        
        provider_class = cls._providers[capability][provider_name]
        return provider_class(model_config)
```

#### 2.2.6 Provider注册（按提供商组织）

```python
# ai/registry.py

from .factory import AIProviderFactory
from .models import ModelCapability

def register_all_providers():
    """注册所有Provider（按提供商组织）"""
    
    # ===== OpenAI提供商 =====
    from .providers.openai.chat import OpenAIChatProvider
    from .providers.openai.vision import OpenAIVisionProvider
    from .providers.openai.dalle import DALLEProvider
    
    AIProviderFactory.register(ModelCapability.CHAT, "openai", OpenAIChatProvider)
    AIProviderFactory.register(ModelCapability.VISION, "openai", OpenAIVisionProvider)
    AIProviderFactory.register(ModelCapability.IMAGE_GEN, "openai_dalle", DALLEProvider)
    
    # ===== Gemini提供商 =====
    from .providers.gemini.chat import GeminiChatProvider
    from .providers.gemini.vision import GeminiVisionProvider
    from .providers.gemini.imagen import ImagenProvider
    
    AIProviderFactory.register(ModelCapability.CHAT, "gemini", GeminiChatProvider)
    AIProviderFactory.register(ModelCapability.VISION, "gemini", GeminiVisionProvider)
    AIProviderFactory.register(ModelCapability.IMAGE_GEN, "gemini_imagen", ImagenProvider)
    
    # ===== Anthropic提供商 =====
    from .providers.anthropic.chat import AnthropicChatProvider
    
    AIProviderFactory.register(ModelCapability.CHAT, "anthropic", AnthropicChatProvider)
    
    # ===== 通义千问 =====
    from .providers.qwen.chat import QwenChatProvider
    from .providers.qwen.image import QwenImageProvider
    
    AIProviderFactory.register(ModelCapability.CHAT, "qwen", QwenChatProvider)
    AIProviderFactory.register(ModelCapability.IMAGE_GEN, "qwen", QwenImageProvider)
    
    # ===== 火山引擎 =====
    from .providers.volcengine_ark.image import VolcengineArkProvider
    
    AIProviderFactory.register(ModelCapability.IMAGE_GEN, "volcengine_ark", VolcengineArkProvider)
    
    # ===== Nano Banana =====
    from .providers.nano_banana.image import NanoBananaProvider
    
    AIProviderFactory.register(ModelCapability.IMAGE_GEN, "nano_banana", NanoBananaProvider)
    
    # ===== OpenAI兼容（跨提供商） =====
    from .providers.openai_compatible.chat import OpenAICompatibleChatProvider
    from .providers.openai_compatible.vision import OpenAICompatibleVisionProvider
    
    AIProviderFactory.register(ModelCapability.CHAT, "openai_compatible", OpenAICompatibleChatProvider)
    AIProviderFactory.register(ModelCapability.VISION, "openai_compatible", OpenAICompatibleVisionProvider)
    
    # ===== 未来扩展 =====
    # from .providers.runway.video import RunwayProvider
    # AIProviderFactory.register(ModelCapability.VIDEO_GEN, "runway", RunwayProvider)
    
    logger.info("所有Provider注册完成")
```

---

## 三、数据库设计

### 3.1 数据库表结构

```sql
-- 数据库迁移：06_ai_model_unified_architecture.sql

-- 1. 添加能力字段（数组）
ALTER TABLE ai_models 
ADD COLUMN IF NOT EXISTS capabilities TEXT[] DEFAULT '{}';

-- 2. 添加Provider映射字段（JSONB）
ALTER TABLE ai_models 
ADD COLUMN IF NOT EXISTS provider_mapping JSONB DEFAULT '{}'::jsonb;

-- 3. 添加索引
CREATE INDEX IF NOT EXISTS idx_ai_models_capabilities 
ON ai_models USING GIN(capabilities);

-- 4. 添加注释
COMMENT ON COLUMN ai_models.capabilities IS '模型支持的能力，如: [chat, vision, image_gen]';
COMMENT ON COLUMN ai_models.provider_mapping IS 'Provider映射，如: {"chat": "openai_compatible", "image_gen": "nano_banana"}';

-- 5. 迁移现有数据
UPDATE ai_models 
SET capabilities = array_remove(ARRAY[
    CASE WHEN supports_chat THEN 'chat' END,
    CASE WHEN supports_vision THEN 'vision' END,
    CASE WHEN supports_image_generation THEN 'image_gen' END
], NULL);

-- 6. 设置默认Provider映射
UPDATE ai_models 
SET provider_mapping = jsonb_build_object(
    CASE WHEN 'chat' = ANY(capabilities) THEN 'chat' END,
    CASE WHEN 'chat' = ANY(capabilities) THEN 'openai_compatible' END,
    
    CASE WHEN 'vision' = ANY(capabilities) THEN 'vision' END,
    CASE WHEN 'vision' = ANY(capabilities) THEN 'openai_compatible' END,
    
    CASE WHEN 'image_gen' = ANY(capabilities) THEN 'image_gen' END,
    CASE WHEN 'image_gen' = ANY(capabilities) THEN provider END
);
```

### 3.2 数据示例

```sql
-- 示例1：GPT-4（Chat + Vision）
INSERT INTO ai_models (
    id, name, provider, ai_model_name, base_url, api_key,
    capabilities, provider_mapping
) VALUES (
    'gpt4-turbo',
    'GPT-4 Turbo',
    'openai',
    'gpt-4-turbo',
    'https://api.openai.com/v1',
    'sk-xxx',
    ARRAY['chat', 'vision'],
    '{"chat": "openai_compatible", "vision": "openai_compatible"}'::jsonb
);

-- 示例2：Gemini Pro（Chat，使用原生）
INSERT INTO ai_models (
    id, name, provider, ai_model_name, base_url, api_key,
    capabilities, provider_mapping
) VALUES (
    'gemini-pro',
    'Gemini Pro',
    'gemini',
    'gemini-pro',
    'https://generativelanguage.googleapis.com/v1',
    'AIza-xxx',
    ARRAY['chat', 'vision'],
    '{"chat": "gemini", "vision": "gemini"}'::jsonb
);

-- 示例3：DALL-E 3（仅ImageGen）
INSERT INTO ai_models (
    id, name, provider, ai_model_name, base_url, api_key,
    capabilities, provider_mapping
) VALUES (
    'dalle3',
    'DALL-E 3',
    'openai_dalle',
    'dall-e-3',
    'https://api.openai.com/v1',
    'sk-xxx',
    ARRAY['image_gen'],
    '{"image_gen": "openai_dalle"}'::jsonb
);

-- 示例4：Nano Banana Pro（ImageGen）
INSERT INTO ai_models (
    id, name, provider, ai_model_name, base_url, api_key,
    capabilities, provider_mapping
) VALUES (
    'nano-banana',
    'Nano Banana Pro',
    'nano_banana',
    'gemini-3-pro-image-preview',
    'https://generativelanguage.googleapis.com/v1',
    'AIza-xxx',
    ARRAY['image_gen'],
    '{"image_gen": "nano_banana"}'::jsonb
);
```

---

## 四、前端设计

### 4.1 前端类型定义

```typescript
// frontend/src/types/ai-model.ts

export enum ModelCapability {
  CHAT = 'chat',
  VISION = 'vision',
  IMAGE_GEN = 'image_gen',
  VIDEO_GEN = 'video_gen',
  EMBEDDINGS = 'embeddings'
}

export interface ModelData {
  id: string
  name: string
  modelName: string
  baseUrl: string
  apiKey: string
  
  // 能力和Provider映射
  capabilities: ModelCapability[]
  providerMapping: Record<ModelCapability, string>
  
  isEnabled: boolean
  isDefault: boolean
}

// Provider选项配置
export interface ProviderOption {
  label: string
  value: string
  capabilities: ModelCapability[]
}
```

### 4.2 前端配置页面

```vue
<!-- frontend/src/views/Settings/ModelManagement.vue -->

<template>
  <div class="model-management">
    <!-- 模型列表 -->
    <el-table :data="models">
      <el-table-column label="模型名称" width="200">
        <template #default="{ row }">
          <div>{{ row.name }}</div>
          <div class="text-xs text-gray-500">{{ row.modelName }}</div>
        </template>
      </el-table-column>
      
      <!-- 能力标签 -->
      <el-table-column label="能力">
        <template #default="{ row }">
          <el-tag
            v-for="cap in row.capabilities"
            :key="cap"
            :type="getCapabilityType(cap)"
            size="small"
            class="mr-1"
          >
            {{ getCapabilityLabel(cap) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <!-- Provider -->
      <el-table-column label="Provider">
        <template #default="{ row }">
          <div class="text-sm">
            <div v-for="(provider, cap) in row.providerMapping" :key="cap">
              <span class="text-gray-500">{{ getCapabilityLabel(cap) }}:</span>
              {{ provider }}
            </div>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'add' ? '添加模型' : '编辑模型'"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item label="模型名称">
          <el-input v-model="form.name" placeholder="如: GPT-4 Turbo" />
        </el-form-item>
        
        <el-form-item label="模型标识">
          <el-input v-model="form.modelName" placeholder="如: gpt-4-turbo" />
        </el-form-item>
        
        <el-form-item label="Base URL">
          <el-input v-model="form.baseUrl" />
        </el-form-item>
        
        <el-form-item label="API Key">
          <el-input v-model="form.apiKey" type="password" show-password />
        </el-form-item>
        
        <el-divider>能力配置</el-divider>
        
        <!-- 能力选择 -->
        <el-form-item label="支持能力">
          <el-checkbox-group v-model="form.capabilities">
            <el-checkbox label="chat">对话</el-checkbox>
            <el-checkbox label="vision">多模态</el-checkbox>
            <el-checkbox label="image_gen">文生图</el-checkbox>
            <el-checkbox label="video_gen">文生视频</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <!-- Provider选择（按能力） -->
        <template v-for="cap in form.capabilities" :key="cap">
          <el-form-item :label="`${getCapabilityLabel(cap)} Provider`">
            <el-select v-model="form.providerMapping[cap]">
              <el-option
                v-for="provider in getProviderOptions(cap)"
                :key="provider.value"
                :label="provider.label"
                :value="provider.value"
              />
            </el-select>
          </el-form-item>
        </template>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ModelData, ModelCapability, ProviderOption } from '@/types/ai-model'

// Provider选项配置
const providerOptions: Record<ModelCapability, ProviderOption[]> = {
  chat: [
    { label: 'OpenAI兼容', value: 'openai_compatible', capabilities: ['chat'] },
    { label: 'Gemini', value: 'gemini', capabilities: ['chat'] },
    { label: 'Anthropic', value: 'anthropic', capabilities: ['chat'] }
  ],
  vision: [
    { label: 'OpenAI兼容', value: 'openai_compatible', capabilities: ['vision'] },
    { label: 'Gemini', value: 'gemini', capabilities: ['vision'] }
  ],
  image_gen: [
    { label: 'OpenAI DALL-E', value: 'openai_dalle', capabilities: ['image_gen'] },
    { label: 'Nano Banana', value: 'nano_banana', capabilities: ['image_gen'] },
    { label: 'Gemini Imagen', value: 'gemini_imagen', capabilities: ['image_gen'] },
    { label: '通义万相', value: 'qwen', capabilities: ['image_gen'] },
    { label: '火山引擎', value: 'volcengine_ark', capabilities: ['image_gen'] }
  ],
  video_gen: [
    { label: 'Runway', value: 'runway', capabilities: ['video_gen'] },
    { label: 'Pika', value: 'pika', capabilities: ['video_gen'] }
  ]
}

const getProviderOptions = (capability: ModelCapability) => {
  return providerOptions[capability] || []
}

const getCapabilityLabel = (capability: string) => {
  const labels = {
    chat: '对话',
    vision: '多模态',
    image_gen: '文生图',
    video_gen: '文生视频'
  }
  return labels[capability] || capability
}

const getCapabilityType = (capability: string) => {
  const types = {
    chat: 'primary',
    vision: 'success',
    image_gen: 'warning',
    video_gen: 'danger'
  }
  return types[capability] || ''
}
</script>
```

---

## 五、实施方案

### 5.1 迁移步骤

#### 阶段一：创建新架构（1周）

**Day 1-2: 核心架构和基类**
```bash
# 创建目录结构（按提供商组织）
mkdir -p backend/app/core/ai/providers/{base,openai,gemini,anthropic,qwen,volcengine_ark,nano_banana,openai_compatible}

# 实现核心文件
touch backend/app/core/ai/{base.py,models.py,factory.py,registry.py,tracker.py}

# 创建能力基类
touch backend/app/core/ai/providers/base/{chat.py,vision.py,image_gen.py,video_gen.py}
```

实现内容：
- `base.py`: `BaseAIProvider`
- `models.py`: `ModelCapability`
- `factory.py`: `AIProviderFactory`
- `registry.py`: `register_all_providers()`
- `tracker.py`: 统一的MLflow追踪（合并llm和imggen的tracker）
- `providers/base/*.py`: 各能力的基类定义

**Day 3-4: OpenAI和OpenAI兼容Provider**
```python
# OpenAI提供商
backend/app/core/ai/providers/openai/client.py
backend/app/core/ai/providers/openai/chat.py
backend/app/core/ai/providers/openai/vision.py
backend/app/core/ai/providers/openai/dalle.py

# OpenAI兼容提供商
backend/app/core/ai/providers/openai_compatible/client.py
backend/app/core/ai/providers/openai_compatible/chat.py
backend/app/core/ai/providers/openai_compatible/vision.py
```

**Day 5: Gemini和Anthropic Provider**
```python
# Gemini提供商
backend/app/core/ai/providers/gemini/client.py
backend/app/core/ai/providers/gemini/chat.py
backend/app/core/ai/providers/gemini/vision.py

# Anthropic提供商
backend/app/core/ai/providers/anthropic/client.py
backend/app/core/ai/providers/anthropic/chat.py
```

#### 阶段二：迁移ImageGen Provider（3-4天）

**Day 1-2: 迁移Provider到对应提供商目录**
```bash
# 迁移Gemini Imagen
# 从 app/core/imggen/providers/gemini.py 
# 迁移到 app/core/ai/providers/gemini/imagen.py

# 迁移Nano Banana
# 从 app/core/imggen/providers/nano_banana.py 
# 迁移到 app/core/ai/providers/nano_banana/image.py

# 迁移通义万相
# 从 app/core/imggen/providers/qwen.py 
# 迁移到 app/core/ai/providers/qwen/image.py

# 迁移火山引擎
# 从 app/core/imggen/providers/volcengine_ark.py 
# 迁移到 app/core/ai/providers/volcengine_ark/image.py

# 修改每个Provider：
# 1. 继承新的 BaseImageGenProvider（从 providers/base/image_gen.py）
# 2. 如果可以，提取共享的client到 client.py
```

**Day 3: 更新Service层和工厂**
```python
# 更新Service层调用
backend/app/services/image/image_generation_service.py

# 更新registry注册（使用新的Provider路径）
backend/app/core/ai/registry.py
```

**Day 4: 测试**
```bash
# 运行测试确保文生图功能正常
pytest tests/unit/test_image_generation.py
pytest tests/integration/test_images.py
```

#### 阶段三：数据库迁移（1天）

```bash
# 执行数据库迁移
docker exec -i ai-pptist-postgres psql -U postgres -d ai_pptist < \
  docker/database/init-scripts/06_ai_model_unified_architecture.sql

# 验证
docker exec -it ai-pptist-postgres psql -U postgres -d ai_pptist \
  -c "SELECT id, name, capabilities, provider_mapping FROM ai_models;"
```

#### 阶段四：前端更新（2-3天）

**Day 1: 更新类型定义**
```typescript
frontend/src/types/ai-model.ts
```

**Day 2-3: 更新ModelManagement页面**
```vue
frontend/src/views/Settings/ModelManagement.vue
```

#### 阶段五：清理和测试（2天）

**Day 1: 清理旧代码**
```bash
# 备份后删除旧架构
mv backend/app/core/llm backend/app/core/llm.bak
mv backend/app/core/imggen backend/app/core/imggen.bak
```

**Day 2: 全面测试**
```bash
# 后端测试
pytest tests/

# 前端测试
npm run test

# E2E测试
npm run test:e2e
```

### 5.2 时间安排

| 阶段 | 任务 | 工作量 | 累计 |
|------|------|--------|------|
| 阶段一 | 创建新架构 | 5天 | 5天 |
| 阶段二 | 迁移ImageGen | 4天 | 9天 |
| 阶段三 | 数据库迁移 | 1天 | 10天 |
| 阶段四 | 前端更新 | 3天 | 13天 |
| 阶段五 | 清理测试 | 2天 | 15天 |

**总计**: 3周（15个工作日）

### 5.3 风险控制

**策略**: 渐进式迁移，保持双架构并存

```python
# backend/main.py

# 阶段一：双架构并存
from app.core.ai.registry import register_all_providers as register_ai_providers
from app.core.imggen import register_all_providers as register_imggen_providers

@asynccontextmanager
async def lifespan(_: FastAPI):
    # 新架构（Chat, Vision）
    register_ai_providers()
    
    # 旧架构（ImageGen，临时保留）
    register_imggen_providers()
    
    yield

# 阶段二：完全切换到新架构
# 删除 register_imggen_providers()
```

---

## 六、总结

### 6.1 核心优势

| 维度 | 改进 |
|------|------|
| **架构统一** | LLM和ImgGen使用同样的Provider模式 |
| **代码简化** | 去除重复代码，统一MLflow追踪 |
| **扩展便利** | 新增能力只需5步，新增Provider只需3步 |
| **维护成本** | 单一架构，降低学习和维护成本 |

### 6.2 扩展示例

**场景1: 新增文生视频能力（未来）**:

```python
# 1. 在base/目录添加能力基类
# ai/providers/base/video_gen.py
class BaseVideoGenProvider(BaseAIProvider):
    def get_capabilities(self) -> Set[ModelCapability]:
        return {ModelCapability.VIDEO_GEN}
    
    @abstractmethod
    async def generate_video(self, prompt: str, **kwargs):
        pass

# 2. 创建提供商目录和实现
# ai/providers/runway/client.py
class RunwayClient:
    def __init__(self, model_config):
        self.client = runway.AsyncClient(api_key=model_config.api_key)

# ai/providers/runway/video.py
from ..base.video_gen import BaseVideoGenProvider
from .client import RunwayClient

class RunwayProvider(BaseVideoGenProvider, RunwayClient):
    def get_provider_name(self) -> str:
        return "runway"
    
    async def generate_video(self, prompt: str, **kwargs):
        # 实现...

# 3. 注册
# ai/registry.py
from .providers.runway.video import RunwayProvider
AIProviderFactory.register(ModelCapability.VIDEO_GEN, "runway", RunwayProvider)

# 4. 前端添加video_gen能力选项
# 5. 用户配置模型时选择video_gen能力和runway Provider
```

**场景2: 为现有提供商新增能力**:

```python
# 例如：为Gemini新增图片生成能力

# 1. 在gemini/目录下添加新文件
# ai/providers/gemini/imagen.py
from ..base.image_gen import BaseImageGenProvider
from .client import GeminiClient  # ⭐ 复用现有client

class ImagenProvider(BaseImageGenProvider, GeminiClient):
    def get_provider_name(self) -> str:
        return "gemini_imagen"
    
    async def generate_image(self, prompt: str, **kwargs):
        # 复用GeminiClient的client和错误处理
        pass

# 2. 注册
AIProviderFactory.register(ModelCapability.IMAGE_GEN, "gemini_imagen", ImagenProvider)
```

**完成！新能力/Provider已集成，代码复用最大化。**

---

**方案特点**:
- ✅ **简单清晰**: 没有过度设计，按提供商组织代码
- ✅ **统一架构**: LLM和ImgGen使用同样的Provider模式
- ✅ **代码复用**: 同一提供商共享client、配置、错误处理
- ✅ **易于维护**: API升级只需修改一个提供商目录
- ✅ **易于扩展**: 新增能力或Provider成本低
- ✅ **渐进迁移**: 双架构并存，风险可控

**实施建议**: 3周完成，渐进式迁移，双架构并存过渡。

---

## 附录：代码组织方案对比

本方案采用**混合方案（按提供商组织为主 + 基类独立）**，详细对比分析请参考：
- 📄 `docs/arch/Provider代码组织方式对比分析.md`

**核心优势总结**:

| 对比项 | 按能力组织 | ⭐ 按提供商组织（本方案） |
|--------|-----------|------------------------|
| **代码复用** | ⭐⭐ OpenAI的chat和image无法共享 | ⭐⭐⭐⭐⭐ 同一提供商共享client |
| **维护成本** | ⭐⭐⭐ 需要跨多个能力目录 | ⭐⭐⭐⭐⭐ 在一个提供商目录内 |
| **API升级** | ⭐⭐ 需要更新多个目录 | ⭐⭐⭐⭐⭐ 只改一个提供商目录 |
| **项目适配** | ⭐⭐⭐ 能力少时适合 | ⭐⭐⭐⭐⭐ 提供商多时适合（本项目10+提供商）|

**决策依据**: 项目有10+提供商但只有5种能力，按提供商组织更合理。

