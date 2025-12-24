-- 06_image_parsing_tables.sql - 图片解析功能相关表结构定义
-- 创建图片解析任务相关的数据库表

-- 设置搜索路径
SET search_path TO public;

-- 创建解析任务状态枚举类型
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'parse_task_status') THEN
        CREATE TYPE parse_task_status AS ENUM ('pending', 'processing', 'completed', 'failed');
    END IF;
END
$$;

-- 创建图片解析任务表
CREATE TABLE IF NOT EXISTS image_parse_tasks (
    -- 主键
    id VARCHAR(50) PRIMARY KEY,

    -- 关联信息
    slide_id VARCHAR(100) NOT NULL,               -- 关联的幻灯片ID
    cos_key TEXT NOT NULL,                        -- 原始图片COS Key（受控输入）

    -- 任务配置
    parse_options JSONB,                          -- 解析选项配置（预留扩展）

    -- 任务状态
    status parse_task_status NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,          -- 进度 0-100

    -- 解析结果
    text_regions JSONB,                           -- 解析出的文字区域（JSON格式）
    metadata JSONB,                               -- 解析元数据（耗时、引擎等）

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- 错误信息
    error_message TEXT,

    -- 用户关联
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_parse_tasks_slide_id ON image_parse_tasks(slide_id);
CREATE INDEX IF NOT EXISTS idx_parse_tasks_user_id ON image_parse_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_parse_tasks_status ON image_parse_tasks(status);
CREATE INDEX IF NOT EXISTS idx_parse_tasks_created_at ON image_parse_tasks(created_at DESC);

-- 添加表注释
COMMENT ON TABLE image_parse_tasks IS '图片解析任务表';
COMMENT ON COLUMN image_parse_tasks.text_regions IS '解析出的文字区域，包含文字内容、位置、置信度等信息';
COMMENT ON COLUMN image_parse_tasks.metadata IS '解析元数据，包含解析耗时、OCR引擎、文字数量等';

-- 为image_parse_tasks表创建更新时间触发器
-- 每次更新记录时自动更新updated_at字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_parse_tasks_updated_at') THEN
        CREATE TRIGGER trigger_parse_tasks_updated_at
            BEFORE UPDATE ON image_parse_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;
