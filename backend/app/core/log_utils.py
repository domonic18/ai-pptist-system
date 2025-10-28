"""
统一日志管理模块
提供标准化的日志记录功能，遵循行业最佳实践
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.log_messages import log_messages


class UnifiedLogger:
    """统一的业务日志记录器，提供结构化日志记录功能"""

    def __init__(self, name: str):
        """初始化日志记录器"""
        self.logger = logging.getLogger(name)  
        self.name = name

    def _format_extra_data(self, **kwargs: Any) -> Dict[str, Any]:
        """格式化日志额外数据"""
        return log_messages.get_structured_data(
            log_module=self.name,
            **kwargs
        )

    def info(self, message_template: str, **kwargs: Any) -> None:
        """
        记录信息级别日志
        
        Args:
            message_template: 日志消息，可以是格式化模板或已格式化的字符串
            **kwargs: 格式化参数（可选）
        
        示例:
            logger.info("简单消息")
            logger.info(f"已格式化的消息: {value}")
            logger.info("{operation} 完成", operation="测试")
        """
        # 只有提供了格式化参数时才进行格式化，避免双重格式化问题
        if kwargs:
            try:
                message = log_messages.format_message(message_template, **kwargs)
            except (KeyError, ValueError):
                # 如果格式化失败，使用原始消息
                message = message_template
        else:
            message = message_template
        
        extra_data = self._format_extra_data(**kwargs)
        self.logger.info(message, extra=extra_data)

    def error(self, message_template: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        记录错误级别日志
        
        Args:
            message_template: 日志消息，可以是格式化模板或已格式化的字符串
            exception: 异常对象（可选）
            **kwargs: 格式化参数（可选）
        """
        # 只有提供了格式化参数时才进行格式化
        if kwargs:
            try:
                message = log_messages.format_message(message_template, **kwargs)
            except (KeyError, ValueError):
                message = message_template
        else:
            message = message_template
        
        extra_data = self._format_extra_data(**kwargs)

        if exception:
            extra_data.update({
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            })
            self.logger.error(message, extra=extra_data, exc_info=exception)
        else:
            self.logger.error(message, extra=extra_data)

    def warning(self, message_template: str, **kwargs: Any) -> None:
        """
        记录警告级别日志
        
        Args:
            message_template: 日志消息，可以是格式化模板或已格式化的字符串
            **kwargs: 格式化参数（可选）
        """
        # 只有提供了格式化参数时才进行格式化
        if kwargs:
            try:
                message = log_messages.format_message(message_template, **kwargs)
            except (KeyError, ValueError):
                message = message_template
        else:
            message = message_template
        
        extra_data = self._format_extra_data(**kwargs)
        self.logger.warning(message, extra=extra_data)

    def debug(self, message_template: str, **kwargs: Any) -> None:
        """
        记录调试级别日志
        
        Args:
            message_template: 日志消息，可以是格式化模板或已格式化的字符串
            **kwargs: 格式化参数（可选）
        """
        if settings.app_debug:
            # 只有提供了格式化参数时才进行格式化
            if kwargs:
                try:
                    message = log_messages.format_message(message_template, **kwargs)
                except (KeyError, ValueError):
                    message = message_template
            else:
                message = message_template
            
            extra_data = self._format_extra_data(**kwargs)
            self.logger.debug(message, extra=extra_data)

    def critical(self, message_template: str, **kwargs: Any) -> None:
        """
        记录严重错误级别日志
        
        Args:
            message_template: 日志消息，可以是格式化模板或已格式化的字符串
            **kwargs: 格式化参数（可选）
        """
        # 只有提供了格式化参数时才进行格式化
        if kwargs:
            try:
                message = log_messages.format_message(message_template, **kwargs)
            except (KeyError, ValueError):
                message = message_template
        else:
            message = message_template
        
        extra_data = self._format_extra_data(**kwargs)
        self.logger.critical(message, extra=extra_data)


# 全局日志实例缓存
_loggers_cache: Dict[str, UnifiedLogger] = {}


def get_logger(name: str = __name__) -> UnifiedLogger:
    """
    获取统一的业务日志记录器

    Args:
        name: 日志记录器名称，默认为当前模块名

    Returns:
        UnifiedLogger实例
    """
    if name not in _loggers_cache:
        _loggers_cache[name] = UnifiedLogger(name)
    return _loggers_cache[name]


def setup_logging() -> None:
    """配置全局日志系统"""
    # 确保日志目录存在
    log_dir = Path(settings.workspace_dir) / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    log_level = logging.DEBUG if settings.app_debug else logging.INFO
    root_logger.setLevel(log_level)

    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建文件处理器
    log_file_path = log_dir / settings.log_file
    # 确保日志文件所在目录存在
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # 创建格式化器
    formatter = logging.Formatter(settings.log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器到根日志记录器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 设置第三方库的日志级别
    third_party_loggers = ["uvicorn", "fastapi", "sqlalchemy", "aiosqlite"]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)  

    # 获取当前模块的日志记录器记录配置完成
    config_logger = get_logger(__name__)
    config_logger.info(log_messages.OPERATION_SUCCESS, operation_name="日志系统配置")


# 导出常用函数别名，方便使用
logger = get_logger