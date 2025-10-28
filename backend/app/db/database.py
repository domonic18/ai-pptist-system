"""
数据库配置模块
SQLAlchemy数据库连接配置
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.db_echo,
    poolclass=NullPool,  # 对于开发环境使用NullPool
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

