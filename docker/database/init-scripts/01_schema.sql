-- 01_schema.sql - 数据库表结构定义
-- 创建所有数据库表结构

-- 设置搜索路径
SET search_path TO public;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    avatar_url VARCHAR(500),
    bio TEXT,
    preferences JSONB DEFAULT '{}'::jsonb
);

-- 创建图片表
CREATE TABLE IF NOT EXISTS images (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT,  -- 改为可为空
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    original_filename VARCHAR(255),  -- 改为可为空
    file_size BIGINT,  -- 改为可为空
    mime_type VARCHAR(100),  -- 改为可为空
    width INTEGER,
    height INTEGER,
    source_type VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    storage_status VARCHAR(20) NOT NULL DEFAULT 'active',
    generation_model VARCHAR(100),  -- 添加generation_model字段
    image_url TEXT,
    cos_key VARCHAR(500),
    cos_bucket VARCHAR(100),
    cos_region VARCHAR(50),
    local_path VARCHAR(500),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 创建PPT演示文稿表
CREATE TABLE IF NOT EXISTS presentations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    template_type VARCHAR(50),
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    settings JSONB DEFAULT '{}'::jsonb,
    thumbnail_url VARCHAR(500),
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 创建幻灯片表
CREATE TABLE IF NOT EXISTS slides (
    id VARCHAR(36) PRIMARY KEY,
    presentation_id VARCHAR(36) NOT NULL REFERENCES presentations(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    order_index INTEGER NOT NULL DEFAULT 0,
    background JSONB DEFAULT '{}'::jsonb,
    animations JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建图片使用关系表
CREATE TABLE IF NOT EXISTS slide_images (
    id VARCHAR(36) PRIMARY KEY,
    slide_id VARCHAR(36) NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
    image_id VARCHAR(36) NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position JSONB NOT NULL DEFAULT '{}'::jsonb,
    size JSONB NOT NULL DEFAULT '{}'::jsonb,
    transform JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slide_id, image_id)
);

-- 创建AI模型配置表
CREATE TABLE IF NOT EXISTS ai_models (
    -- 基本字段
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    ai_model_name VARCHAR(255) NOT NULL,

    -- API配置
    base_url VARCHAR(512),
    api_key TEXT NOT NULL,

    -- 模型配置
    model_settings JSONB,

    -- 状态管理
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,

    -- 能力配置
    supports_chat BOOLEAN DEFAULT TRUE,
    supports_embeddings BOOLEAN DEFAULT FALSE,
    supports_vision BOOLEAN DEFAULT FALSE,
    supports_tools BOOLEAN DEFAULT FALSE,
    supports_image_generation BOOLEAN DEFAULT FALSE,

    -- 限制配置
    max_tokens VARCHAR(20) DEFAULT '8192',
    context_window VARCHAR(20) DEFAULT '16384',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);



-- 创建标签表
CREATE TABLE IF NOT EXISTS tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);



-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);
CREATE INDEX IF NOT EXISTS idx_images_is_public ON images(is_public);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at);
CREATE INDEX IF NOT EXISTS idx_images_tags ON images USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_presentations_user_id ON presentations(user_id);
CREATE INDEX IF NOT EXISTS idx_presentations_is_public ON presentations(is_public);
CREATE INDEX IF NOT EXISTS idx_presentations_status ON presentations(status);
CREATE INDEX IF NOT EXISTS idx_presentations_created_at ON presentations(created_at);

CREATE INDEX IF NOT EXISTS idx_slides_presentation_id ON slides(presentation_id);
CREATE INDEX IF NOT EXISTS idx_slides_user_id ON slides(user_id);
CREATE INDEX IF NOT EXISTS idx_slides_order_index ON slides(order_index);

CREATE INDEX IF NOT EXISTS idx_slide_images_slide_id ON slide_images(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_images_image_id ON slide_images(image_id);
CREATE INDEX IF NOT EXISTS idx_slide_images_user_id ON slide_images(user_id);

-- 为AI模型表创建索引
CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON ai_models(provider);
CREATE INDEX IF NOT EXISTS idx_ai_models_enabled ON ai_models(is_enabled);
CREATE INDEX IF NOT EXISTS idx_ai_models_default ON ai_models(is_default);
CREATE INDEX IF NOT EXISTS idx_ai_models_created_at ON ai_models(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_models_image_generation ON ai_models(supports_image_generation);

-- 为标签表创建索引
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags(usage_count);
CREATE INDEX IF NOT EXISTS idx_tags_created_at ON tags(created_at);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要自动更新时间的表创建触发器
DO $$
BEGIN
    -- users表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_users_updated_at') THEN
        CREATE TRIGGER trigger_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- images表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_images_updated_at') THEN
        CREATE TRIGGER trigger_images_updated_at
            BEFORE UPDATE ON images
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- presentations表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_presentations_updated_at') THEN
        CREATE TRIGGER trigger_presentations_updated_at
            BEFORE UPDATE ON presentations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- slides表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_slides_updated_at') THEN
        CREATE TRIGGER trigger_slides_updated_at
            BEFORE UPDATE ON slides
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- slide_images表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_slide_images_updated_at') THEN
        CREATE TRIGGER trigger_slide_images_updated_at
            BEFORE UPDATE ON slide_images
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- ai_models表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_ai_models_updated_at') THEN
        CREATE TRIGGER trigger_ai_models_updated_at
            BEFORE UPDATE ON ai_models
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- tags表
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_tags_updated_at') THEN
        CREATE TRIGGER trigger_tags_updated_at
            BEFORE UPDATE ON tags
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;