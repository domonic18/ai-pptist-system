"""
日志系统单元测试
遵循项目测试规范：快速执行，无外部依赖

测试 UnifiedLogger 的核心功能，特别是双重格式化问题的修复
"""

import pytest
import logging
from unittest.mock import patch

from app.core.log_utils import UnifiedLogger, get_logger
from app.core.log_messages import LogMessages


@pytest.mark.unit
@pytest.mark.logging
class TestUnifiedLogger:
    """UnifiedLogger 单元测试类"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.logger_name = "test_logger"
        self.unified_logger = UnifiedLogger(self.logger_name)
        
    def test_init(self):
        """测试 UnifiedLogger 初始化"""
        assert self.unified_logger.name == self.logger_name
        assert isinstance(self.unified_logger.logger, logging.Logger)
        assert self.unified_logger.logger.name == self.logger_name

    def test_info_with_simple_message(self):
        """测试记录简单消息（无格式化参数）"""
        with patch.object(self.unified_logger.logger, 'info') as mock_info:
            message = "简单的日志消息"
            self.unified_logger.info(message)
            
            # 验证底层 logger 被调用
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            # 验证消息内容
            assert call_args[0][0] == message
            assert 'extra' in call_args[1]
            assert 'log_module' in call_args[1]['extra']

    def test_info_with_formatted_string(self):
        """测试记录已经通过 f-string 格式化的消息（包含字典）"""
        with patch.object(self.unified_logger.logger, 'info') as mock_info:
            # 模拟包含字典的已格式化消息
            result = {"image_id": "123", "tags": ["测试", "标签"]}
            message = f"操作完成，结果: {result}"
            
            # 不应该抛出 KeyError
            self.unified_logger.info(message)
            
            # 验证调用
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            # 验证消息包含字典内容
            assert "image_id" in call_args[0][0]
            assert "123" in call_args[0][0]

    def test_info_with_format_parameters(self):
        """测试使用格式化参数的消息"""
        with patch.object(self.unified_logger.logger, 'info') as mock_info:
            template = "操作 {operation_name} 完成"
            operation_name = "测试操作"
            
            self.unified_logger.info(template, operation_name=operation_name)
            
            # 验证调用
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            # 验证消息已被格式化
            assert call_args[0][0] == f"操作 {operation_name} 完成"
            assert 'extra' in call_args[1]
            assert call_args[1]['extra']['operation_name'] == operation_name

    def test_info_with_invalid_format(self):
        """测试格式化失败时的降级处理"""
        with patch.object(self.unified_logger.logger, 'info') as mock_info:
            # 提供不匹配的格式化模板和参数
            template = "操作 {operation_name} 完成"
            
            # 应该使用原始消息，不抛出异常
            self.unified_logger.info(template, wrong_param="测试")
            
            # 验证使用了原始消息
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert call_args[0][0] == template

    def test_error_with_exception(self):
        """测试记录带异常的错误日志"""
        with patch.object(self.unified_logger.logger, 'error') as mock_error:
            message = "发生错误"
            test_exception = ValueError("测试异常")
            
            self.unified_logger.error(message, exception=test_exception)
            
            # 验证调用
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            
            # 验证消息和异常信息
            assert call_args[0][0] == message
            assert 'extra' in call_args[1]
            assert call_args[1]['extra']['exception_type'] == 'ValueError'
            assert call_args[1]['extra']['exception_message'] == '测试异常'
            assert call_args[1]['exc_info'] == test_exception

    def test_error_without_exception(self):
        """测试记录不带异常的错误日志"""
        with patch.object(self.unified_logger.logger, 'error') as mock_error:
            message = "错误消息"
            
            self.unified_logger.error(message)
            
            # 验证调用
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            
            assert call_args[0][0] == message
            assert 'exc_info' not in call_args[1]

    def test_error_with_formatted_dict(self):
        """测试错误日志中包含字典的情况"""
        with patch.object(self.unified_logger.logger, 'error') as mock_error:
            error_data = {"error_code": 500, "details": "内部错误"}
            message = f"错误详情: {error_data}"
            
            # 不应该抛出 KeyError
            self.unified_logger.error(message)
            
            # 验证调用
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "error_code" in call_args[0][0]

    def test_warning_with_simple_message(self):
        """测试记录警告日志"""
        with patch.object(self.unified_logger.logger, 'warning') as mock_warning:
            message = "警告消息"
            
            self.unified_logger.warning(message)
            
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert call_args[0][0] == message

    def test_warning_with_formatted_dict(self):
        """测试警告日志中包含字典的情况"""
        with patch.object(self.unified_logger.logger, 'warning') as mock_warning:
            warning_data = {"user_id": "user123", "action": "未授权操作"}
            message = f"警告: {warning_data}"
            
            self.unified_logger.warning(message)
            
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "user_id" in call_args[0][0]

    @patch('app.core.log_utils.settings')
    def test_debug_when_debug_enabled(self, mock_settings):
        """测试在调试模式开启时记录调试日志"""
        mock_settings.app_debug = True
        
        with patch.object(self.unified_logger.logger, 'debug') as mock_debug:
            message = "调试消息"
            
            self.unified_logger.debug(message)
            
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args
            assert call_args[0][0] == message

    @patch('app.core.log_utils.settings')
    def test_debug_when_debug_disabled(self, mock_settings):
        """测试在调试模式关闭时不记录调试日志"""
        mock_settings.app_debug = False
        
        with patch.object(self.unified_logger.logger, 'debug') as mock_debug:
            message = "调试消息"
            
            self.unified_logger.debug(message)
            
            # 调试模式关闭时不应该调用底层 logger
            mock_debug.assert_not_called()

    def test_critical_with_simple_message(self):
        """测试记录严重错误日志"""
        with patch.object(self.unified_logger.logger, 'critical') as mock_critical:
            message = "严重错误"
            
            self.unified_logger.critical(message)
            
            mock_critical.assert_called_once()
            call_args = mock_critical.call_args
            assert call_args[0][0] == message

    def test_critical_with_formatted_dict(self):
        """测试严重错误日志中包含字典的情况"""
        with patch.object(self.unified_logger.logger, 'critical') as mock_critical:
            critical_data = {"system": "database", "status": "down"}
            message = f"系统故障: {critical_data}"
            
            self.unified_logger.critical(message)
            
            mock_critical.assert_called_once()
            call_args = mock_critical.call_args
            assert "system" in call_args[0][0]


@pytest.mark.unit
@pytest.mark.logging
class TestGetLogger:
    """测试 get_logger 工厂函数"""

    def test_get_logger_returns_unified_logger(self):
        """测试 get_logger 返回 UnifiedLogger 实例"""
        logger = get_logger("test_module")
        
        assert isinstance(logger, UnifiedLogger)
        assert logger.name == "test_module"

    def test_get_logger_caching(self):
        """测试 get_logger 的缓存机制"""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        # 应该返回同一个实例
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """测试不同名称返回不同的 logger 实例"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        # 应该返回不同的实例
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"


@pytest.mark.unit
@pytest.mark.logging
class TestLogMessages:
    """测试 LogMessages 类"""

    def test_format_message_simple(self):
        """测试简单消息格式化"""
        log_messages = LogMessages()
        result = log_messages.format_message(
            "操作 {operation_name} 完成",
            operation_name="测试"
        )
        
        assert result == "操作 测试 完成"

    def test_format_message_multiple_params(self):
        """测试多参数消息格式化"""
        log_messages = LogMessages()
        result = log_messages.format_message(
            "用户 {user_id} 执行了 {action}",
            user_id="user123",
            action="删除操作"
        )
        
        assert result == "用户 user123 执行了 删除操作"

    def test_get_structured_data(self):
        """测试获取结构化数据"""
        log_messages = LogMessages()
        data = log_messages.get_structured_data(
            user_id="user123",
            action="test_action",
            count=5
        )
        
        assert data == {
            "user_id": "user123",
            "action": "test_action",
            "count": 5
        }


@pytest.mark.unit
@pytest.mark.logging
class TestRealWorldScenarios:
    """测试真实世界的使用场景"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.logger = UnifiedLogger("test_service")

    def test_tag_service_batch_operation_scenario(self):
        """
        测试标签服务批量操作场景
        这是导致原始 bug 的场景
        """
        with patch.object(self.logger.logger, 'info') as mock_info:
            # 模拟批量操作返回的结果
            result = {
                "image_id": "d5f1cabc-bf11-447f-9712-91e7059886a4",
                "added_tags": ["测试"],
                "current_tags": ["AI生成", "宫殿", "测试标签", "单个测试", "测试", "修复验证"],
                "total": 6
            }
            
            # 这种调用方式之前会导致 KeyError: 'image_id'
            # 现在应该正常工作
            message = f"添加标签操作完成，返回结果: {result}"
            self.logger.info(message)
            
            # 验证日志记录成功
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            # 验证消息包含所有预期内容
            assert "image_id" in call_args[0][0]
            assert "d5f1cabc-bf11-447f-9712-91e7059886a4" in call_args[0][0]
            assert "added_tags" in call_args[0][0]

    def test_mixed_logging_patterns(self):
        """测试混合使用不同的日志模式"""
        with patch.object(self.logger.logger, 'info') as mock_info:
            # 模式1: 简单消息
            self.logger.info("开始处理请求")
            
            # 模式2: f-string 格式化
            user_id = "user123"
            self.logger.info(f"用户 {user_id} 发起请求")
            
            # 模式3: 包含字典的 f-string
            data = {"count": 10, "status": "success"}
            self.logger.info(f"处理完成，结果: {data}")
            
            # 模式4: 使用格式化参数
            self.logger.info("操作 {operation} 完成", operation="测试")
            
            # 验证所有调用都成功
            assert mock_info.call_count == 4

    def test_error_logging_with_exception_and_dict(self):
        """测试同时包含异常和字典的错误日志"""
        with patch.object(self.logger.logger, 'error') as mock_error:
            error_context = {
                "operation": "batch_tag_update",
                "image_ids": ["id1", "id2"],
                "failed_count": 2
            }
            exception = ValueError("标签验证失败")
            
            message = f"批量操作失败，上下文: {error_context}"
            self.logger.error(message, exception=exception)
            
            # 验证调用
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            
            # 验证包含字典内容和异常信息
            assert "operation" in call_args[0][0]
            assert "batch_tag_update" in call_args[0][0]
            assert call_args[1]['extra']['exception_type'] == 'ValueError'
            assert call_args[1]['exc_info'] == exception

