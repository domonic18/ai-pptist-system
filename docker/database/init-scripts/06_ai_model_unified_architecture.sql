-- ========================================
-- AI模型统一架构 - 数据库迁移脚本
-- 版本: v2.0
-- 日期: 2025-12-21
-- 说明: 添加capabilities和provider_mapping字段，支持统一的AI模型管理
-- ========================================

-- 1. 添加能力字段（数组）
ALTER TABLE ai_models 
ADD COLUMN IF NOT EXISTS capabilities TEXT[] DEFAULT '{}';

-- 2. 添加Provider映射字段（JSONB）
ALTER TABLE ai_models 
ADD COLUMN IF NOT EXISTS provider_mapping JSONB DEFAULT '{}'::jsonb;

-- 3. 为capabilities创建GIN索引（支持数组查询）
CREATE INDEX IF NOT EXISTS idx_ai_models_capabilities 
ON ai_models USING GIN(capabilities);

-- 4. 为provider_mapping创建GIN索引（支持JSONB查询）
CREATE INDEX IF NOT EXISTS idx_ai_models_provider_mapping 
ON ai_models USING GIN(provider_mapping);

-- 5. 添加注释
COMMENT ON COLUMN ai_models.capabilities IS '模型支持的能力列表，如: [chat, vision, image_gen, video_gen]';
COMMENT ON COLUMN ai_models.provider_mapping IS 'Provider映射配置，如: {"chat": "openai", "image_gen": "openai_dalle"}';

-- 6. 迁移现有数据 - 根据旧字段推导新字段
UPDATE ai_models 
SET capabilities = array_remove(ARRAY[
    CASE WHEN supports_chat THEN 'chat' END,
    CASE WHEN supports_vision THEN 'vision' END,
    CASE WHEN supports_image_generation THEN 'image_gen' END,
    CASE WHEN supports_embeddings THEN 'embeddings' END,
    CASE WHEN supports_tools THEN 'tools' END
], NULL)
WHERE capabilities = '{}';  -- 只更新未设置的记录

-- 7. 设置默认的provider_mapping
-- 7.1 Chat能力默认使用openai_compatible
UPDATE ai_models 
SET provider_mapping = jsonb_set(
    COALESCE(provider_mapping, '{}'::jsonb),
    '{chat}',
    '"openai_compatible"'::jsonb
)
WHERE 'chat' = ANY(capabilities) 
  AND (provider_mapping->>'chat' IS NULL OR provider_mapping = '{}'::jsonb);

-- 7.2 Vision能力默认使用openai_compatible
UPDATE ai_models 
SET provider_mapping = jsonb_set(
    COALESCE(provider_mapping, '{}'::jsonb),
    '{vision}',
    '"openai_compatible"'::jsonb
)
WHERE 'vision' = ANY(capabilities)
  AND (provider_mapping->>'vision' IS NULL);

-- 7.3 ImageGen能力根据provider字段设置
UPDATE ai_models 
SET provider_mapping = jsonb_set(
    COALESCE(provider_mapping, '{}'::jsonb),
    '{image_gen}',
    to_jsonb(COALESCE(provider, 'openai_dalle'))
)
WHERE 'image_gen' = ANY(capabilities)
  AND (provider_mapping->>'image_gen' IS NULL);

-- 8. 创建查询视图 - 方便查看模型能力
CREATE OR REPLACE VIEW v_ai_models_with_capabilities AS
SELECT 
    id,
    name,
    provider,
    ai_model_name,
    base_url,
    capabilities,
    provider_mapping,
    is_enabled,
    is_default,
    -- 展开能力标签（用于快速筛选）
    'chat' = ANY(capabilities) as has_chat,
    'vision' = ANY(capabilities) as has_vision,
    'image_gen' = ANY(capabilities) as has_image_gen,
    'video_gen' = ANY(capabilities) as has_video_gen,
    'embeddings' = ANY(capabilities) as has_embeddings,
    'tools' = ANY(capabilities) as has_tools,
    created_at,
    updated_at
FROM ai_models;

-- 9. 创建函数：根据能力查询模型
CREATE OR REPLACE FUNCTION get_models_by_capability(
    required_capability TEXT
) RETURNS SETOF ai_models AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM ai_models
    WHERE required_capability = ANY(capabilities)
    AND is_enabled = TRUE
    ORDER BY is_default DESC, created_at DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_models_by_capability(TEXT) IS '根据单个能力查询可用模型';

-- 10. 创建函数：根据多个能力查询模型
CREATE OR REPLACE FUNCTION get_models_by_capabilities(
    required_capabilities TEXT[]
) RETURNS SETOF ai_models AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM ai_models
    WHERE capabilities @> required_capabilities  -- 包含所有需要的能力
    AND is_enabled = TRUE
    ORDER BY is_default DESC, created_at DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_models_by_capabilities(TEXT[]) IS '根据多个能力查询可用模型（必须支持所有能力）';

-- 11. 创建函数：获取模型的Provider
CREATE OR REPLACE FUNCTION get_model_provider(
    model_id_param TEXT,
    capability TEXT
) RETURNS TEXT AS $$
DECLARE
    provider_name TEXT;
BEGIN
    SELECT provider_mapping->>capability INTO provider_name
    FROM ai_models
    WHERE id = model_id_param;
    
    RETURN provider_name;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_model_provider(TEXT, TEXT) IS '获取指定模型的指定能力对应的Provider名称';

-- 12. 创建触发器：确保provider_mapping与capabilities一致
CREATE OR REPLACE FUNCTION check_provider_mapping_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- 检查provider_mapping中的每个key是否在capabilities中
    IF NEW.provider_mapping IS NOT NULL THEN
        DECLARE
            mapping_key TEXT;
        BEGIN
            FOR mapping_key IN SELECT jsonb_object_keys(NEW.provider_mapping)
            LOOP
                IF NOT (mapping_key = ANY(NEW.capabilities)) THEN
                    RAISE WARNING 'Provider mapping key % not in capabilities', mapping_key;
                END IF;
            END LOOP;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_provider_mapping
BEFORE INSERT OR UPDATE ON ai_models
FOR EACH ROW
EXECUTE FUNCTION check_provider_mapping_consistency();

COMMENT ON TRIGGER trigger_check_provider_mapping ON ai_models IS '确保provider_mapping的key与capabilities一致';

-- 13. 数据统计查询（用于验证迁移）
DO $$
DECLARE
    total_models INTEGER;
    models_with_capabilities INTEGER;
    models_with_provider_mapping INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_models FROM ai_models;
    SELECT COUNT(*) INTO models_with_capabilities FROM ai_models WHERE array_length(capabilities, 1) > 0;
    SELECT COUNT(*) INTO models_with_provider_mapping FROM ai_models WHERE provider_mapping != '{}'::jsonb;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'AI模型统一架构迁移完成';
    RAISE NOTICE '========================================';
    RAISE NOTICE '总模型数: %', total_models;
    RAISE NOTICE '已设置capabilities的模型: %', models_with_capabilities;
    RAISE NOTICE '已设置provider_mapping的模型: %', models_with_provider_mapping;
    RAISE NOTICE '========================================';
END $$;

