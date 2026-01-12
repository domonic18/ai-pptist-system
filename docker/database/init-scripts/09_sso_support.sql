-- 09_sso_support.sql - SSO认证支持
-- 添加用户认证和会话管理相关表和字段

-- 设置搜索路径
SET search_path TO public;

-- ==================== 1. 扩展users表，添加SSO相关字段 ====================

-- 添加认证类型字段（password/saml）
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20) DEFAULT 'password';

-- 添加SAML NameID（用户在IDP的唯一标识）
ALTER TABLE users ADD COLUMN IF NOT EXISTS saml_name_id VARCHAR(255);

-- 添加SAML SessionIndex（SAML会话索引）
ALTER TABLE users ADD COLUMN IF NOT EXISTS saml_session_index VARCHAR(255);

-- 添加SAML属性（存储IDP返回的用户属性）
ALTER TABLE users ADD COLUMN IF NOT EXISTS saml_attributes JSONB DEFAULT '{}'::jsonb;

-- 添加最后SSO登录时间
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_sso_login_at TIMESTAMP WITH TIME ZONE;

-- 添加约束：确保auth_type只能是password或saml
ALTER TABLE users ADD CONSTRAINT chk_auth_type
    CHECK (auth_type IN ('password', 'saml'));

-- 添加注释
COMMENT ON COLUMN users.auth_type IS '认证类型: password=账号密码登录, saml=SSO单点登录';
COMMENT ON COLUMN users.saml_name_id IS 'SAML NameID，用户在IDP的唯一标识';
COMMENT ON COLUMN users.saml_session_index IS 'SAML SessionIndex，用于会话管理';
COMMENT ON COLUMN users.saml_attributes IS 'SAML返回的用户属性，JSON格式存储';
COMMENT ON COLUMN users.last_sso_login_at IS '最后一次SSO登录时间';

-- 为SSO相关字段添加索引
CREATE INDEX IF NOT EXISTS idx_users_auth_type ON users(auth_type);
CREATE INDEX IF NOT EXISTS idx_users_saml_name_id ON users(saml_name_id);
CREATE INDEX IF NOT EXISTS idx_users_saml_session_index ON users(saml_session_index);


-- ==================== 2. 创建用户会话表 ====================

CREATE TABLE IF NOT EXISTS user_sessions (
    -- 主键
    id VARCHAR(36) PRIMARY KEY,

    -- 用户关联
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Token标识
    token_jti VARCHAR(255) UNIQUE NOT NULL,           -- JWT ID (access_token的jti)
    refresh_token_jti VARCHAR(255) UNIQUE,            -- 刷新令牌的JWT ID

    -- 会话信息
    user_agent TEXT,                                  -- 用户代理（浏览器信息）
    ip_address VARCHAR(45),                           -- IP地址（支持IPv6）

    -- 过期时间
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,     -- access_token过期时间
    refresh_expires_at TIMESTAMP WITH TIME ZONE,      -- refresh_token过期时间

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE               -- 撤销时间（NULL表示活跃）
);

-- 添加注释
COMMENT ON TABLE user_sessions IS '用户会话表，存储JWT token会话信息';
COMMENT ON COLUMN user_sessions.token_jti IS 'JWT Token的唯一标识（jti claim）';
COMMENT ON COLUMN user_sessions.refresh_token_jti IS '刷新Token的唯一标识';
COMMENT ON COLUMN user_sessions.expires_at IS '访问令牌过期时间';
COMMENT ON COLUMN user_sessions.refresh_expires_at IS '刷新令牌过期时间';
COMMENT ON COLUMN user_sessions.revoked_at IS '会话撤销时间，NULL表示会话活跃';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_jti ON user_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_token_jti ON user_sessions(refresh_token_jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_revoked_at ON user_sessions(revoked_at);


-- ==================== 3. 创建登录历史表 ====================

CREATE TABLE IF NOT EXISTS login_history (
    -- 主键
    id VARCHAR(36) PRIMARY KEY,

    -- 用户关联（可为空，用于记录未成功的登录尝试）
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,

    -- 认证信息
    auth_type VARCHAR(20) NOT NULL,                   -- 认证类型: password 或 saml
    login_status VARCHAR(20) NOT NULL,                -- 登录状态: success, failed
    failure_reason VARCHAR(255),                      -- 失败原因（如果登录失败）

    -- 请求信息
    ip_address VARCHAR(45),                           -- IP地址
    user_agent TEXT,                                  -- 用户代理

    -- SSO相关信息
    saml_name_id VARCHAR(255),                        -- SAML登录时记录NameID

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 添加注释
COMMENT ON TABLE login_history IS '用户登录历史记录表';
COMMENT ON COLUMN login_history.auth_type IS '认证类型: password=账号密码, saml=SSO单点登录';
COMMENT ON COLUMN login_history.login_status IS '登录状态: success=成功, failed=失败';
COMMENT ON COLUMN login_history.failure_reason IS '登录失败的原因描述';
COMMENT ON COLUMN login_history.saml_name_id IS 'SSO登录时的SAML NameID';

-- 添加约束：确保login_status只能是success或failed
ALTER TABLE login_history ADD CONSTRAINT chk_login_status
    CHECK (login_status IN ('success', 'failed'));

-- 添加约束：确保auth_type只能是password或saml
ALTER TABLE login_history ADD CONSTRAINT chk_login_auth_type
    CHECK (auth_type IN ('password', 'saml'));

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_auth_type ON login_history(auth_type);
CREATE INDEX IF NOT EXISTS idx_login_history_status ON login_history(login_status);
CREATE INDEX IF NOT EXISTS idx_login_history_created_at ON login_history(created_at);
CREATE INDEX IF NOT EXISTS idx_login_history_saml_name_id ON login_history(saml_name_id);


-- ==================== 4. 创建触发器：自动更新user_sessions的updated_at字段 ====================

-- 为user_sessions表添加updated_at字段（如果还没有）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_sessions'
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE user_sessions ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- 创建触发器
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_user_sessions_updated_at') THEN
        CREATE TRIGGER trigger_user_sessions_updated_at
            BEFORE UPDATE ON user_sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;


-- ==================== 5. 创建辅助视图 ====================

-- 创建活跃会话视图（只显示未撤销且未过期的会话）
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT
    us.id,
    us.user_id,
    u.email,
    u.name,
    us.token_jti,
    us.ip_address,
    us.user_agent,
    us.expires_at,
    us.created_at,
    us.updated_at
FROM user_sessions us
JOIN users u ON us.user_id = u.id
WHERE us.revoked_at IS NULL
  AND us.expires_at > CURRENT_TIMESTAMP;

COMMENT ON VIEW v_active_sessions IS '活跃用户会话视图';


-- 创建登录统计视图
CREATE OR REPLACE VIEW v_login_stats AS
SELECT
    u.id,
    u.email,
    u.name,
    u.auth_type,
    COUNT(lh.id) FILTER (WHERE lh.login_status = 'success') AS total_logins,
    COUNT(lh.id) FILTER (WHERE lh.login_status = 'failed') AS failed_logins,
    MAX(lh.created_at) FILTER (WHERE lh.login_status = 'success') AS last_login_at,
    MAX(lh.created_at) FILTER (WHERE lh.login_status = 'failed') AS last_failed_at
FROM users u
LEFT JOIN login_history lh ON u.id = lh.user_id
GROUP BY u.id, u.email, u.name, u.auth_type;

COMMENT ON VIEW v_login_stats IS '用户登录统计视图';


-- ==================== 6. 创建清理过期会话的函数 ====================

CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除已过期且已撤销的会话（过期超过1天）
    DELETE FROM user_sessions
    WHERE revoked_at IS NOT NULL
      AND expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- 记录清理日志
    RAISE NOTICE '已清理 % 个过期会话', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_sessions IS '清理过期的用户会话，返回删除的会话数';


-- ==================== 7. 数据回滚函数（如需回滚使用） ====================

-- 创建回滚函数（仅用于开发调试，生产环境慎用）
CREATE OR REPLACE FUNCTION rollback_sso_support()
RETURNS VOID AS $$
BEGIN
    -- 删除视图
    DROP VIEW IF EXISTS v_login_stats;
    DROP VIEW IF EXISTS v_active_sessions;

    -- 删除函数
    DROP FUNCTION IF EXISTS cleanup_expired_sessions();

    -- 删除触发器
    DROP TRIGGER IF EXISTS trigger_user_sessions_updated_at ON user_sessions;

    -- 删除表
    DROP TABLE IF EXISTS login_history;
    DROP TABLE IF EXISTS user_sessions;

    -- 删除users表的新增字段
    ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_auth_type;
    ALTER TABLE users DROP COLUMN IF EXISTS last_sso_login_at;
    ALTER TABLE users DROP COLUMN IF EXISTS saml_attributes;
    ALTER TABLE users DROP COLUMN IF EXISTS saml_session_index;
    ALTER TABLE users DROP COLUMN IF EXISTS saml_name_id;
    ALTER TABLE users DROP COLUMN IF EXISTS auth_type;

    RAISE NOTICE 'SSO支持已回滚';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION rollback_sso_support IS '回滚SSO支持的所有更改（仅用于开发调试）';


-- ==================== 8. 初始化现有用户的auth_type ====================

-- 为现有用户设置auth_type（如果为NULL）
UPDATE users
SET auth_type = 'password'
WHERE auth_type IS NULL OR auth_type = '';


-- ==================== 完成提示 ====================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'SSO认证支持数据库迁移完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '新增内容:';
    RAISE NOTICE '  1. users表新增5个SSO相关字段';
    RAISE NOTICE '  2. 新建user_sessions表（会话管理）';
    RAISE NOTICE '  3. 新建login_history表（登录历史）';
    RAISE NOTICE '  4. 新建2个视图：v_active_sessions, v_login_stats';
    RAISE NOTICE '  5. 新建清理函数：cleanup_expired_sessions()';
    RAISE NOTICE '  6. 新建回滚函数：rollback_sso_support()';
    RAISE NOTICE '========================================';
    RAISE NOTICE '如需回滚，执行: SELECT rollback_sso_support();';
    RAISE NOTICE '========================================';
END $$;
