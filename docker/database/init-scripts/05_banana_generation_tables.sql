-- 05_banana_generation_tables.sql - Banana生成功能相关表结构定义
-- 创建Banana生成任务相关的数据库表

-- 设置搜索路径
SET search_path TO public;

-- 创建生成任务状态枚举类型
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'banana_task_status') THEN
        CREATE TYPE banana_task_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
    END IF;
END
$$;

-- 创建Banana生成任务表
CREATE TABLE IF NOT EXISTS banana_generation_tasks (
    -- 主键
    id VARCHAR(50) PRIMARY KEY,
    
    -- 用户信息
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    
    -- 任务配置
    outline JSONB NOT NULL,                    -- 大纲数据
    template_id VARCHAR(50) NOT NULL,          -- 模板ID
    template_image_url TEXT,                   -- 模板图片URL（COS或本地）
    generation_model VARCHAR(100) NOT NULL,    -- 生成模型名称（如 gemini-3-pro-image-preview）
    canvas_size JSONB NOT NULL,                -- 画布尺寸 {"width": 1920, "height": 1080}
    
    -- 任务状态
    status banana_task_status NOT NULL DEFAULT 'pending',
    
    -- 进度信息
    total_slides INTEGER NOT NULL DEFAULT 0,
    completed_slides INTEGER NOT NULL DEFAULT 0,
    failed_slides INTEGER NOT NULL DEFAULT 0,
    
    -- 生成结果（存储每页的生成状态和图片URL）
    slides_data JSONB,
    
    -- 错误信息
    error_message TEXT,
    
    -- Celery任务信息
    celery_task_id VARCHAR(100),               -- Celery任务ID（用于监控）
    celery_group_id VARCHAR(100),              -- Celery任务组ID（批量任务）
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 创建Banana模板表（可选，用于管理模板）
CREATE TABLE IF NOT EXISTS banana_templates (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 图片信息
    cover_url TEXT NOT NULL,                   -- 缩略图URL
    full_image_url TEXT NOT NULL,              -- 完整图片URL（用于生成参考）
    
    -- 模板配置
    type VARCHAR(20) NOT NULL DEFAULT 'system', -- system | user
    aspect_ratio VARCHAR(10) NOT NULL DEFAULT '16:9',
    
    -- 用户信息（用户上传模板时使用）
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    
    -- 使用统计
    usage_count INTEGER NOT NULL DEFAULT 0,
    
    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_banana_tasks_user_id ON banana_generation_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_banana_tasks_status ON banana_generation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_banana_tasks_created_at ON banana_generation_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_banana_tasks_celery_task_id ON banana_generation_tasks(celery_task_id);
CREATE INDEX IF NOT EXISTS idx_banana_tasks_template_id ON banana_generation_tasks(template_id);

CREATE INDEX IF NOT EXISTS idx_banana_templates_type ON banana_templates(type);
CREATE INDEX IF NOT EXISTS idx_banana_templates_user_id ON banana_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_banana_templates_is_active ON banana_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_banana_templates_usage_count ON banana_templates(usage_count);

-- 为Banana表创建更新时间触发器
DO $$
BEGIN
    -- banana_generation_tasks表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_banana_tasks_updated_at') THEN
        CREATE TRIGGER trigger_banana_tasks_updated_at
            BEFORE UPDATE ON banana_generation_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- banana_templates表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_banana_templates_updated_at') THEN
        CREATE TRIGGER trigger_banana_templates_updated_at
            BEFORE UPDATE ON banana_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

