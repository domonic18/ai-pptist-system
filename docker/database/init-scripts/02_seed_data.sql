-- 02_seed_data.sql - 种子数据初始化
-- 插入系统必需的初始数据

-- 设置搜索路径
SET search_path TO public;

-- 创建默认管理员用户（如果不存在）
INSERT INTO users (id, email, name, password, role, is_active, is_superuser, created_at, updated_at)
SELECT
    'admin_001',
    'admin@ai-ppt.local',
    '系统管理员',
    -- 密码: admin123 (使用bcrypt加密，cost=12)
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'ADMIN',
    TRUE,
    TRUE,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'admin@ai-ppt.local'
);

-- 创建默认普通用户（如果不存在）
INSERT INTO users (id, email, name, password, role, is_active, is_superuser, created_at, updated_at)
SELECT
    'user_001',
    'user@ai-ppt.local',
    '测试用户',
    -- 密码: user123 (使用bcrypt加密，cost=12)
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'USER',
    TRUE,
    FALSE,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'user@ai-ppt.local'
);

-- 创建演示用户（如果不存在）
INSERT INTO users (id, email, name, password, role, is_active, is_superuser, created_at, updated_at)
SELECT
    'demo_001',
    'demo@ai-ppt.local',
    '演示用户',
    -- 密码: demo123 (使用bcrypt加密，cost=12)
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'USER',
    TRUE,
    FALSE,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'demo@ai-ppt.local'
);

-- 注释掉示例图片数据，避免干扰图片上传功能的测试
-- 这些是演示数据，实际使用时应该通过正常的上传流程添加图片

-- 插入示例演示文稿模板（如果不存在）
INSERT INTO presentations (id, user_id, title, description, tags, is_public, is_template, template_type, content, settings, thumbnail_url, version, status, created_at, updated_at, published_at)
SELECT
    'pres_001',
    'admin_001',
    '企业介绍模板',
    '专业的企业介绍演示模板',
    '{"business", "introduction", "corporate"}',
    TRUE,
    TRUE,
    'business',
    '{"slides": [], "theme": "corporate-blue", "layout": "standard"}'::jsonb,
    '{"aspectRatio": "16:9", "fontFamily": "Arial", "primaryColor": "#2563eb"}'::jsonb,
    '/templates/business-intro-thumb.jpg',
    1,
    'published',
    NOW(),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM presentations WHERE id = 'pres_001'
);

INSERT INTO presentations (id, user_id, title, description, tags, is_public, is_template, template_type, content, settings, thumbnail_url, version, status, created_at, updated_at, published_at)
SELECT
    'pres_002',
    'admin_001',
    '产品发布模板',
    '现代风格的产品发布演示模板',
    '{"product", "launch", "modern"}',
    TRUE,
    TRUE,
    'product',
    '{"slides": [], "theme": "modern-orange", "layout": "creative"}'::jsonb,
    '{"aspectRatio": "16:9", "fontFamily": "Inter", "primaryColor": "#f97316"}'::jsonb,
    '/templates/product-launch-thumb.jpg',
    1,
    'published',
    NOW(),
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM presentations WHERE id = 'pres_002'
);

-- 插入默认模型配置（统一架构）
-- 1. OpenAI GPT-4 (对话+多模态)
INSERT INTO ai_models (
    id, name, ai_model_name, base_url, api_key,
    capabilities, provider_mapping,
    parameters, max_tokens, context_window,
    is_enabled, is_default
) VALUES (
    'default-openai-gpt4',
    'OpenAI GPT-4 Turbo',
    'gpt-4-turbo',
    'https://api.openai.com/v1',
    'your-openai-api-key-here',
    ARRAY['chat', 'vision'],
    '{"chat": "openai", "vision": "openai"}'::jsonb,
    '{}'::jsonb,
    128000,
    128000,
    TRUE,
    TRUE
) ON CONFLICT (id) DO NOTHING;

-- 2. OpenAI DALL-E 3 (文生图)
INSERT INTO ai_models (
    id, name, ai_model_name, base_url, api_key,
    capabilities, provider_mapping,
    parameters, max_tokens, context_window,
    is_enabled, is_default
) VALUES (
    'default-openai-dalle3',
    'OpenAI DALL-E 3',
    'dall-e-3',
    'https://api.openai.com/v1',
    'your-openai-api-key-here',
    ARRAY['image_gen'],
    '{"image_gen": "openai_dalle"}'::jsonb,
    '{"quality": "standard", "style": "vivid"}'::jsonb,
    4000,
    4000,
    TRUE,
    FALSE
) ON CONFLICT (id) DO NOTHING;

-- 3. DeepSeek (OpenAI兼容 - 对话)
INSERT INTO ai_models (
    id, name, ai_model_name, base_url, api_key,
    capabilities, provider_mapping,
    parameters, max_tokens, context_window,
    is_enabled, is_default
) VALUES (
    'deepseek-chat',
    'DeepSeek Chat',
    'deepseek-chat',
    'https://api.deepseek.com/v1',
    'your-deepseek-api-key-here',
    ARRAY['chat'],
    '{"chat": "openai_compatible"}'::jsonb,
    '{}'::jsonb,
    8192,
    32768,
    FALSE,
    FALSE
) ON CONFLICT (id) DO NOTHING;


-- 记录初始化完成
DO $$
BEGIN
    RAISE NOTICE '种子数据初始化脚本执行完成';
END $$;