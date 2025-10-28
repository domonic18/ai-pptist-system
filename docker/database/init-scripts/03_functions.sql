-- 03_functions.sql - 数据库函数和工具函数
-- 创建系统需要的存储过程和函数

-- 设置搜索路径
SET search_path TO public;

-- 创建搜索函数 - 根据标签搜索图片
CREATE OR REPLACE FUNCTION search_images_by_tags(
    search_tags TEXT[],
    user_id_param VARCHAR(36) DEFAULT NULL,
    is_public_param BOOLEAN DEFAULT TRUE,
    limit_count INTEGER DEFAULT 50,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id VARCHAR(36),
    user_id VARCHAR(36),
    prompt TEXT,
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN,
    original_filename VARCHAR(255),
    file_size BIGINT,
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    match_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.user_id,
        i.prompt,
        i.description,
        i.tags,
        i.is_public,
        i.original_filename,
        i.file_size,
        i.mime_type,
        i.width,
        i.height,
        i.created_at,
        -- 计算匹配分数：匹配标签数量 * 10
        (SELECT COUNT(*) FROM unnest(search_tags) AS st
         WHERE st = ANY(i.tags)) * 10 AS match_score
    FROM images i
    WHERE
        -- 权限检查：公开或用户自己的图片
        (i.is_public = TRUE OR i.user_id = user_id_param)
        AND i.storage_status = 'active'
        AND i.deleted_at IS NULL
        AND (
            -- 至少匹配一个标签
            EXISTS (SELECT 1 FROM unnest(search_tags) AS st WHERE st = ANY(i.tags))
            OR array_length(search_tags, 1) IS NULL
        )
    ORDER BY match_score DESC, i.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- 创建统计函数 - 用户图片统计
CREATE OR REPLACE FUNCTION get_user_image_stats(
    user_id_param VARCHAR(36)
)
RETURNS TABLE (
    total_images BIGINT,
    total_size BIGINT,
    public_images BIGINT,
    private_images BIGINT,
    avg_image_size BIGINT,
    last_upload_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_images,
        COALESCE(SUM(file_size), 0)::BIGINT AS total_size,
        COUNT(*) FILTER (WHERE is_public = TRUE)::BIGINT AS public_images,
        COUNT(*) FILTER (WHERE is_public = FALSE)::BIGINT AS private_images,
        COALESCE(AVG(file_size), 0)::BIGINT AS avg_image_size,
        MAX(created_at) AS last_upload_date
    FROM images
    WHERE
        user_id = user_id_param
        AND storage_status = 'active'
        AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- 创建清理函数 - 标记删除过期图片
CREATE OR REPLACE FUNCTION cleanup_old_images(
    days_old INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 标记超过指定天数的图片为已删除
    UPDATE images
    SET
        storage_status = 'deleted',
        deleted_at = NOW()
    WHERE
        created_at < NOW() - (days_old || ' days')::INTERVAL
        AND storage_status = 'active'
        AND deleted_at IS NULL
        AND is_public = FALSE;  -- 只清理非公开图片

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 创建搜索函数 - 全文搜索演示文稿
CREATE OR REPLACE FUNCTION search_presentations(
    search_query TEXT,
    user_id_param VARCHAR(36) DEFAULT NULL,
    is_public_param BOOLEAN DEFAULT TRUE,
    limit_count INTEGER DEFAULT 50,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id VARCHAR(36),
    user_id VARCHAR(36),
    title VARCHAR(255),
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN,
    is_template BOOLEAN,
    status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE,
    match_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.user_id,
        p.title,
        p.description,
        p.tags,
        p.is_public,
        p.is_template,
        p.status,
        p.created_at,
        -- 简单的匹配分数计算
        CASE
            WHEN p.title ILIKE '%' || search_query || '%' THEN 30
            WHEN p.description ILIKE '%' || search_query || '%' THEN 20
            WHEN EXISTS (SELECT 1 FROM unnest(p.tags) AS tag WHERE tag ILIKE '%' || search_query || '%') THEN 10
            ELSE 0
        END AS match_score
    FROM presentations p
    WHERE
        -- 权限检查
        (p.is_public = is_public_param OR p.user_id = user_id_param)
        AND p.status = 'published'
        AND p.deleted_at IS NULL
        AND (
            p.title ILIKE '%' || search_query || '%'
            OR p.description ILIKE '%' || search_query || '%'
            OR EXISTS (SELECT 1 FROM unnest(p.tags) AS tag WHERE tag ILIKE '%' || search_query || '%')
        )
    ORDER BY match_score DESC, p.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- 创建获取用户活动统计函数
CREATE OR REPLACE FUNCTION get_user_activity_stats(
    user_id_param VARCHAR(36)
)
RETURNS TABLE (
    total_presentations BIGINT,
    total_slides BIGINT,
    published_presentations BIGINT,
    draft_presentations BIGINT,
    templates_created BIGINT,
    last_activity_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT p.id)::BIGINT AS total_presentations,
        COUNT(s.id)::BIGINT AS total_slides,
        COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'published')::BIGINT AS published_presentations,
        COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'draft')::BIGINT AS draft_presentations,
        COUNT(DISTINCT p.id) FILTER (WHERE p.is_template = TRUE)::BIGINT AS templates_created,
        GREATEST(MAX(p.updated_at), MAX(s.updated_at)) AS last_activity_date
    FROM presentations p
    LEFT JOIN slides s ON p.id = s.presentation_id
    WHERE
        p.user_id = user_id_param
        AND p.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- 记录函数创建完成
DO $$
BEGIN
    RAISE NOTICE '数据库函数初始化脚本执行完成';
END $$;