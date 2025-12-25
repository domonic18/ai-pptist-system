-- 07_image_editing_tables.sql - 图片编辑功能增强相关表结构定义
-- 创建图片编辑任务相关的数据库表（混合OCR + 文字去除）

-- 设置搜索路径
SET search_path TO public;

-- 创建编辑任务状态枚举类型
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'editing_task_status') THEN
        CREATE TYPE editing_task_status AS ENUM (
            'pending',           -- 等待处理
            'ocr_processing',    -- OCR识别中
            'text_removal',      -- 去除文字中
            'completed',         -- 完成
            'failed'             -- 失败
        );
    END IF;
END
$$;

-- 创建图片编辑任务表
CREATE TABLE IF NOT EXISTS image_editing_tasks (
    -- 主键
    id VARCHAR(50) PRIMARY KEY,

    -- 关联信息
    slide_id VARCHAR(100) NOT NULL,               -- 关联的幻灯片ID
    original_cos_key TEXT NOT NULL,               -- 原始图片COS Key
    edited_cos_key TEXT,                          -- 编辑后的图片COS Key

    -- 任务状态
    status editing_task_status NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,          -- 进度 0-100
    current_step VARCHAR(50),                     -- 当前处理步骤

    -- 任务配置
    edit_options JSONB,                           -- 编辑选项配置

    -- OCR结果（混合OCR识别结果）
    ocr_result JSONB,                             -- 混合OCR识别结果

    -- 文字去除结果
    removal_result JSONB,                         -- 文字去除结果

    -- 元数据
    metadata JSONB,                               -- 处理元数据（总耗时等）

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
CREATE INDEX IF NOT EXISTS idx_editing_tasks_slide_id ON image_editing_tasks(slide_id);
CREATE INDEX IF NOT EXISTS idx_editing_tasks_user_id ON image_editing_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_editing_tasks_status ON image_editing_tasks(status);
CREATE INDEX IF NOT EXISTS idx_editing_tasks_created_at ON image_editing_tasks(created_at DESC);

-- 添加表注释
COMMENT ON TABLE image_editing_tasks IS '图片编辑任务表（混合OCR + 文字去除）';
COMMENT ON COLUMN image_editing_tasks.ocr_result IS '混合OCR识别结果，包含传统OCR和多模态大模型的融合数据';
COMMENT ON COLUMN image_editing_tasks.removal_result IS '文字去除结果，包含新图片URL、处理模型、耗时等';
COMMENT ON COLUMN image_editing_tasks.metadata IS '处理元数据，包含总耗时、各步骤耗时、识别数量等';

-- 为image_editing_tasks表创建更新时间触发器
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_editing_tasks_updated_at') THEN
        CREATE TRIGGER trigger_editing_tasks_updated_at
            BEFORE UPDATE ON image_editing_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;
