-- 08_alter_banana_tasks_template_id_nullable.sql
-- 修改banana_generation_tasks表的template_id字段为可空
-- 用于支持自定义模板上传功能

-- 设置搜索路径
SET search_path TO public;

-- 修改template_id字段为可空
-- 允许用户使用自定义上传的图片作为模板（不需要template_id）
DO $$
BEGIN
    -- 检查约束是否存在并删除
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'banana_generation_tasks_template_id_fkey'
    ) THEN
        ALTER TABLE banana_generation_tasks
        DROP CONSTRAINT banana_generation_tasks_template_id_fkey;
    END IF;

    -- 修改字段为可空
    ALTER TABLE banana_generation_tasks
    ALTER COLUMN template_id DROP NOT NULL;

    -- 重新创建外键约束（如果需要）
    -- 注意：如果banana_templates表存在，则重新创建外键
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'banana_templates') THEN
        ALTER TABLE banana_generation_tasks
        ADD CONSTRAINT banana_generation_tasks_template_id_fkey
        FOREIGN KEY (template_id) REFERENCES banana_templates(id) ON DELETE SET NULL;
    END IF;

    RAISE NOTICE 'template_id字段已修改为可空';
END
$$;

-- 添加注释
COMMENT ON COLUMN banana_generation_tasks.template_id IS '模板ID（系统模板时引用banana_templates，自定义模板时为NULL）';
