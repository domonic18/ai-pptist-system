# 部署脚本说明

## deploy.sh - 环境管理脚本

### 功能
- 统一管理生产环境和开发环境的部署
- 提供完整的服务生命周期管理
- 支持日志查看、状态监控、数据清理等功能

### 使用方法

```bash
# 显示帮助信息
./scripts/deploy.sh help

# 启动开发环境
./scripts/deploy.sh dev up

# 启动生产环境
./scripts/deploy.sh prod up

# 查看开发环境日志
./scripts/deploy.sh dev logs

# 查看特定服务日志
./scripts/deploy.sh dev logs backend

# 停止生产环境
./scripts/deploy.sh prod down

# 重启开发环境
./scripts/deploy.sh dev restart

# 查看容器状态
./scripts/deploy.sh dev ps

# 进入容器
./scripts/deploy.sh dev exec backend

# 清理开发环境数据
./scripts/deploy.sh dev clean
```

### 环境配置

#### 生产环境 (config/.env)
- 包含生产环境的所有配置参数
- 需要从 `.env.example` 复制并修改
- 包含敏感信息，不要提交到版本控制

#### 开发环境 (config/.env.local)
- 包含开发环境的配置参数
- 可选文件，不存在时会使用默认值
- 用于本地开发和测试

### 数据库初始化

数据库初始化脚本位于 `docker/database/init-scripts/`:

1. **01_schema.sql** - 表结构定义
2. **02_seed_data.sql** - 种子数据
3. **03_functions.sql** - 数据库函数

PostgreSQL 容器启动时会自动按顺序执行这些脚本。

### 数据持久化

- **生产环境**: `workspace/db_data`, `workspace/redis_data`
- **开发环境**: `workspace/db_data_dev`, `workspace/redis_data_dev`

使用 `clean` 命令可以清理这些数据目录。