"""
数据库配置模块
SQLAlchemy数据库连接配置
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.db_echo,
    # 使用 QueuePool 替代 NullPool，提供更好的连接管理
    poolclass=QueuePool,
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接健康检查
    pool_recycle=3600,  # 连接回收时间（秒）
    # 设置连接超时，避免无限等待
    connect_args={
        "server_settings": {
            "lock_timeout": "5s",  # 锁等待超时
            "statement_timeout": "30s",  # 语句执行超时
        }
    },
    future=True
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 声明性基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    获取数据库会话依赖
    用于FastAPI依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()

