-- 04_annotation_tables.sql - 标注功能相关表结构定义
-- 创建标注相关的数据库表

-- 设置搜索路径
SET search_path TO public;

-- 创建标注任务状态枚举类型
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'annotation_task_status') THEN
        CREATE TYPE annotation_task_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
    END IF;
END
$$;

-- 创建标注任务表
CREATE TABLE IF NOT EXISTS annotation_tasks (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    presentation_id VARCHAR(36) NOT NULL REFERENCES presentations(id) ON DELETE CASCADE,
    status annotation_task_status NOT NULL DEFAULT 'pending',

    -- 任务配置
    model_id VARCHAR(50) REFERENCES ai_models(id),
    model_config JSONB,
    extraction_config JSONB,

    -- 进度信息
    total_pages INTEGER NOT NULL DEFAULT 0,
    completed_pages INTEGER NOT NULL DEFAULT 0,
    failed_pages INTEGER NOT NULL DEFAULT 0,

    -- 统计信息
    average_confidence FLOAT NOT NULL DEFAULT 0.0,
    total_corrections INTEGER NOT NULL DEFAULT 0,

    -- 时间信息
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 创建幻灯片标注结果表
CREATE TABLE IF NOT EXISTS slide_annotations (
    id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL REFERENCES annotation_tasks(id) ON DELETE CASCADE,
    slide_id VARCHAR(36) NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,

    -- 页面类型
    page_type VARCHAR(50),
    page_type_confidence FLOAT,
    page_type_reason VARCHAR(500),

    -- 布局类型
    layout_type VARCHAR(50),
    layout_type_confidence FLOAT,
    layout_type_reason VARCHAR(500),

    -- 元素标注（JSON格式）
    element_annotations JSONB,

    -- 整体置信度
    overall_confidence FLOAT,

    -- 用户修正
    user_corrections JSONB,
    has_corrections INTEGER NOT NULL DEFAULT 0,

    -- 时间信息
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 为标注表创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_annotation_tasks_user_id ON annotation_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_annotation_tasks_presentation_id ON annotation_tasks(presentation_id);
CREATE INDEX IF NOT EXISTS idx_annotation_tasks_status ON annotation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_annotation_tasks_created_at ON annotation_tasks(created_at);

CREATE INDEX IF NOT EXISTS idx_slide_annotations_task_id ON slide_annotations(task_id);
CREATE INDEX IF NOT EXISTS idx_slide_annotations_slide_id ON slide_annotations(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_annotations_slide_index ON slide_annotations(slide_index);
CREATE INDEX IF NOT EXISTS idx_slide_annotations_page_type ON slide_annotations(page_type);
CREATE INDEX IF NOT EXISTS idx_slide_annotations_layout_type ON slide_annotations(layout_type);

-- 为标注表创建更新时间触发器
DO $$
BEGIN
    -- annotation_tasks表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_annotation_tasks_updated_at') THEN
        CREATE TRIGGER trigger_annotation_tasks_updated_at
            BEFORE UPDATE ON annotation_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- slide_annotations表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_slide_annotations_updated_at') THEN
        CREATE TRIGGER trigger_slide_annotations_updated_at
            BEFORE UPDATE ON slide_annotations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;