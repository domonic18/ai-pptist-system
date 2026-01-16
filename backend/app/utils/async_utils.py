"""
异步工具模块
提供在同步上下文中运行异步代码的工具函数
"""

import asyncio
from typing import Any, Coroutine, TypeVar
from contextlib import contextmanager

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    在同步上下文中运行异步协程（如 Celery 任务）

    使用方式：
        result = run_async(some_async_function())

    Args:
        coro: 异步协程对象

    Returns:
        协程的返回值
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # 关闭所有未完成的任务
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


@contextmanager
def async_context():
    """
    异步上下文管理器，用于需要多次运行异步代码的场景

    使用方式：
        with async_context() as run:
            result1 = run(async_func1())
            result2 = run(async_func2())
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop.run_until_complete
    finally:
        # 关闭所有未完成的任务
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


class AsyncRunner:
    """
    异步运行器类，用于在同步上下文中运行多个异步操作

    使用 asyncio.run() 来管理事件循环，确保每次都是全新的循环
    并在完成后正确清理数据库连接池

    使用方式：
        with AsyncRunner() as runner:
            result = runner.run(some_async_function())
    """

    def __init__(self):
        # 不再预先创建循环，而是在 run 方法中使用 asyncio.run()
        self._loop = None

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        运行异步协程

        使用 asyncio.run() 创建新的事件循环并运行协程
        这会确保每次都是干净的事件循环状态，并正确清理所有资源
        """
        return asyncio.run(coro)

    def close(self):
        """无需关闭，asyncio.run() 会自动管理"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


