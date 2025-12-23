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
        loop.close()


class AsyncRunner:
    """
    异步运行器类，用于在同步上下文中运行多个异步操作
    
    使用方式：
        runner = AsyncRunner()
        try:
            result1 = runner.run(async_func1())
            result2 = runner.run(async_func2())
        finally:
            runner.close()
    """
    
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
    
    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """运行异步协程"""
        return self._loop.run_until_complete(coro)
    
    def close(self):
        """关闭事件循环"""
        if self._loop and not self._loop.is_closed():
            self._loop.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

