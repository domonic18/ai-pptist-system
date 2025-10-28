# AI PPTist - 测试框架指南

## 概述

本项目采用**分层测试架构**，包括单元测试和集成测试，确保代码质量和系统稳定性。遵循pytest最佳实践，使用统一的conftest.py配置管理，支持测试类型隔离和环境配置。

## 测试架构

### 1. 测试分层
- **单元测试** (`tests/unit/`)：快速执行，无外部依赖，适合CI一级流水线
- **集成测试** (`tests/interface/`)：真实HTTP请求，测试完整业务流程

### 2. 测试特点

#### 单元测试特点
- ✅ **无外部依赖**：不依赖网络、数据库、AI API
- ✅ **快速执行**：毫秒级响应，适合频繁运行
- ✅ **Mock机制**：使用统一的Mock工具库
- ✅ **配置隔离**：使用内存数据库和mock配置

#### 集成测试特点
- ✅ **真实HTTP请求**：通过TestClient向真实服务发送请求
- ✅ **完整业务流程**：测试端到端的用户场景
- ✅ **环境隔离**：可配置测试数据库或使用内存数据库

## 测试目录结构

```
backend/tests/
├── utils/                        # 统一的测试工具库
│   ├── mock_utils.py            # Mock工具和装饰器
│   ├── test_data_utils.py       # 测试数据生成和验证工具
│   └── database_utils.py        # 数据库工具和fixtures
│
├── unit/                         # 单元测试 - 快速、无外部依赖
│   ├── test_imports.py          # 模块导入测试
│   ├── test_image_service.py    # 图片服务测试
│   ├── test_cos_service.py      # COS存储服务测试
│   └── test_*.py                # 其他单元测试
│
├── interface/                    # 接口集成测试
│   ├── test_basic.py            # 基础接口测试
│   ├── test_images.py           # 图片接口测试
│   └── test_*.py                # 其他集成测试
│
├── conftest.py                   # 全局测试配置和fixtures（唯一）
├── pytest.ini                   # pytest配置
├── run_unit_tests.py            # 单元测试专用运行脚本
├── run_integration_tests.py     # 集成测试专用运行脚本
├── run_all_tests.py             # 完整测试运行脚本
└── README.md                     # 本文档
```

## 测试配置管理

### 1. 统一的conftest.py
项目采用**单一conftest.py**模式，位于tests根目录，包含：
- 全局共享fixtures
- 测试环境自动配置
- 测试类型识别和隔离

### 2. 环境配置策略
根据测试标记自动配置环境：
```python
# 单元测试环境
@pytest.mark.unit → 内存数据库 + Mock COS配置

# 集成测试环境
@pytest.mark.integration → 可配置测试数据库
```

## 单元测试维护指南

### 1. 创建新的单元测试

#### 文件位置和命名
```bash
# 在 tests/unit/ 目录下创建
tests/unit/test_[模块名].py

# 示例
tests/unit/test_image_service.py
tests/unit/test_cos_service.py
```

#### 测试类结构
```python
"""
[模块名]单元测试
遵循项目测试规范：快速执行，无外部依赖
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.[模块名] import [服务类]

@pytest.mark.unit
@pytest.mark.[功能标记]
class Test[服务类]:
    """[服务类]单元测试类"""

    def test_[测试方法名](self):
        """测试[功能描述]"""
        # 使用mock对象进行测试
        mock_session = MagicMock()

        # 执行测试
        result = await [服务类].[方法名](mock_session, ...)

        # 验证结果
        assert result is not None
```

#### 必需的测试标记
```python
@pytest.mark.unit                    # 标记为单元测试
@pytest.mark.asyncio                 # 异步测试标记
@pytest.mark.[service_name]          # 服务模块标记
```

### 2. 单元测试运行方式

#### 使用专用运行脚本（推荐）
```bash
# 运行所有单元测试
python tests/run_unit_tests.py

# 运行特定测试文件
python tests/run_unit_tests.py tests/unit/test_image_service.py

# 生成覆盖率报告
python tests/run_unit_tests.py --cov=app --cov-report=html
```

#### 直接使用pytest
```bash
# 运行所有单元测试
pytest tests/unit/ -m unit -v

# 运行特定功能模块测试
pytest tests/unit/ -m "unit and image_service"
pytest tests/unit/ -m "unit and cos_service"

# 运行特定测试文件
pytest tests/unit/test_image_service.py -v
```

## 集成测试运行方式

### 1. 运行集成测试
```bash
# 使用专用运行脚本
python tests/run_integration_tests.py

# 直接使用pytest
pytest tests/interface/ -m integration -v

# 运行特定接口测试
pytest tests/interface/test_images.py -v
```

### 2. 运行所有测试
```bash
# 运行所有测试（单元+集成）
python tests/run_all_tests.py

# 或直接使用pytest
pytest tests/ -v
```

## 最佳实践

### 1. 单元测试原则
- **单一职责**：每个测试只验证一个功能点
- **无外部依赖**：不依赖网络、数据库、外部服务
- **快速执行**：单个测试应在毫秒级完成
- **可重复**：测试结果应稳定一致

### 2. Mock使用原则
- **使用Mock工具**：优先使用 `tests/utils/mock_utils.py` 中的工具
- **最小Mock**：只Mock必要的部分，保持测试的真实性
- **异步Mock**：使用 `AsyncMock` 处理异步方法

### 3. 测试数据管理
- **动态生成**：使用 `TestDataGenerator` 生成测试数据
- **数据验证**：使用 `TestDataValidator` 验证数据结构
- **数据隔离**：每个测试使用独立的测试数据

## 故障排除

### 常见问题
1. **测试环境冲突**：确保使用正确的运行脚本或pytest标记
2. **数据库连接问题**：单元测试使用内存数据库，无需额外配置
3. **异步测试问题**：确保使用 `@pytest.mark.asyncio` 标记异步测试

### 调试技巧
```bash
# 详细输出
pytest -v --tb=short

# 调试特定测试
pytest tests/unit/test_image_service.py::TestImageService::test_create_image_success -v -s

# 查看测试覆盖率
pytest --cov=app --cov-report=term-missing
```

## 总结

本测试框架提供了完整的测试解决方案：

1. **统一配置**：单一conftest.py管理所有测试配置
2. **测试隔离**：单元测试和集成测试环境完全隔离
3. **便捷运行**：专用运行脚本支持不同类型测试
4. **工具完备**：丰富的Mock工具和测试数据管理
5. **最佳实践**：清晰的指导原则和故障排除指南

通过遵循这些规范，您可以构建高质量、可维护的测试套件，确保代码质量和系统稳定性。