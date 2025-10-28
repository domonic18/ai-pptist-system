"""
数据库测试工具
提供数据库测试相关的工具函数和fixtures
"""

import os
import asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import MagicMock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.database import Base
from app.core.config import settings


class DatabaseTestUtils:
    """数据库测试工具类"""

    @staticmethod
    def get_test_database_url() -> str:
        """
        获取测试数据库URL

        Returns:
            str: 测试数据库URL
        """
        # 使用内存数据库进行测试
        return "sqlite+aiosqlite:///:memory:"

    @staticmethod
    async def create_test_tables(engine):
        """
        创建测试表

        Args:
            engine: SQLAlchemy异步引擎
        """
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def drop_test_tables(engine):
        """
        删除测试表

        Args:
            engine: SQLAlchemy异步引擎
        """
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @staticmethod
    def create_mock_session() -> MagicMock:
        """
        创建mock数据库会话

        Returns:
            MagicMock: mock数据库会话对象
        """
        mock_session = MagicMock()

        # 配置mock方法
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.close = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock()
        mock_session.scalar = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.add = MagicMock(return_value=None)
        mock_session.delete = MagicMock(return_value=None)
        mock_session.refresh = AsyncMock(return_value=None)

        return mock_session

    @staticmethod
    def setup_test_environment():
        """设置测试环境变量"""
        # 设置测试环境变量
        os.environ["TESTING"] = "true"
        os.environ["UNIT_TESTING"] = "true"
        os.environ["DATABASE_URL"] = DatabaseTestUtils.get_test_database_url()

        # 设置Mock COS配置
        os.environ["COS_SECRET_ID"] = "test-secret-id"
        os.environ["COS_SECRET_KEY"] = "test-secret-key"
        os.environ["COS_REGION"] = "test-region"
        os.environ["COS_BUCKET"] = "test-bucket"
        os.environ["COS_SCHEME"] = "https"

    @staticmethod
    def teardown_test_environment():
        """清理测试环境变量"""
        # 清理测试环境变量
        for key in ["TESTING", "UNIT_TESTING", "DATABASE_URL",
                   "COS_SECRET_ID", "COS_SECRET_KEY", "COS_REGION",
                   "COS_BUCKET", "COS_SCHEME"]:
            if key in os.environ:
                del os.environ[key]


@pytest.fixture(scope="session")
def event_loop():
    """
    创建事件循环fixture
    用于异步测试
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """
    测试数据库引擎fixture
    """
    test_db_url = DatabaseTestUtils.get_test_database_url()
    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool
    )

    # 创建表
    await DatabaseTestUtils.create_test_tables(engine)

    yield engine

    # 清理表
    await DatabaseTestUtils.drop_test_tables(engine)
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    测试数据库会话fixture
    每个测试函数一个独立的会话
    """
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="function")
def mock_db_session() -> MagicMock:
    """
    mock数据库会话fixture
    """
    return DatabaseTestUtils.create_mock_session()


@pytest.fixture(autouse=True)
async def cleanup_database(test_session):
    """
    自动清理数据库fixture
    在每个测试后清理数据库
    """
    yield

    # 清理所有表数据
    for table in reversed(Base.metadata.sorted_tables):
        await test_session.execute(table.delete())
    await test_session.commit()


def with_test_database(func):
    """
    装饰器：为测试函数提供测试数据库

    Args:
        func: 测试函数

    Returns:
        Callable: 装饰后的函数
    """
    async def wrapper(*args, **kwargs):
        # 创建测试数据库引擎
        test_db_url = DatabaseTestUtils.get_test_database_url()
        engine = create_async_engine(
            test_db_url,
            echo=False,
            poolclass=NullPool
        )

        try:
            # 创建表
            await DatabaseTestUtils.create_test_tables(engine)

            # 创建会话
            async_session = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            async with async_session() as session:
                # 将会话添加到kwargs
                kwargs['test_session'] = session

                # 执行测试函数
                result = await func(*args, **kwargs)

                # 清理数据
                for table in reversed(Base.metadata.sorted_tables):
                    await session.execute(table.delete())
                await session.commit()

                return result

        finally:
            # 清理表并关闭引擎
            await DatabaseTestUtils.drop_test_tables(engine)
            await engine.dispose()

    return wrapper