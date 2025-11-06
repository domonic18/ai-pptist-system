#!/usr/bin/env python3
"""
CSS工具函数单元测试
包含正则表达式、颜色解析、样式处理等工具功能测试
遵循项目测试规范：快速执行，无外部依赖
"""

import pytest
import re
from app.core.html.html_utils import parse_inline_style, parse_px_value, parse_radius_value


@pytest.mark.unit
@pytest.mark.html_parser
class TestCSSUtils:
    """CSS工具函数单元测试类"""

    def test_parse_rgba_regex_patterns(self):
        """测试RGBA颜色正则表达式匹配"""
        # 测试用例
        test_cases = [
            "rgba(67, 97, 238, 0.15)",
            "rgba(255, 0, 0, 0.5)",
            "rgba(0, 128, 255, 0.8)",
            "rgba(10,20,30,1.0)",
            "rgba(255, 255, 255, 0)",
            "rgba(123, 45, 67, 0.99)"
        ]

        # 标准正则表达式模式
        standard_pattern = r'rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)'

        print("测试RGBA正则表达式匹配:")
        for test_case in test_cases:
            match = re.search(standard_pattern, test_case)
            assert match is not None, f"无法匹配RGBA格式: {test_case}"

            opacity = float(match.group(1))
            assert 0.0 <= opacity <= 1.0, f"透明度值超出范围: {opacity}"
            print(f"✅ {test_case} -> 透明度: {opacity}")

    def test_parse_invalid_rgba_patterns(self):
        """测试无效RGBA格式处理"""
        invalid_cases = [
            "rgb(255, 0, 0)",  # 缺少alpha通道，应该不匹配
            "rgba(255, 0)",    # 参数不足，应该不匹配
            "rgba(255, 0, 0, 1.5)",  # 透明度超出范围，但正则会匹配
            "rgba(a, b, c, d)",       # 非数字参数，正则不会匹配
            "rgba(256, 0, 0, 0.5)",   # RGB值超出范围，但正则会匹配
        ]

        pattern = r'rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)'

        for invalid_case in invalid_cases:
            match = re.search(pattern, invalid_case)
            # 对于无效格式，正则表达式可能不匹配或匹配无效值
            if match:
                try:
                    opacity = float(match.group(1))
                    # 正则表达式本身不验证数值范围，只验证格式
                    # 这里主要测试正则不会崩溃，数值验证在业务逻辑中进行
                    assert isinstance(opacity, float), f"无法转换为浮点数: {opacity}"
                except ValueError:
                    # 无法转换为浮点数，这是预期的
                    pass

    def test_parse_inline_style_function(self):
        """测试内联样式解析函数"""
        # 基本样式解析
        style_str = "position: absolute; left: 100px; top: 200px; width: 150px; height: 80px"
        result = parse_inline_style(style_str)

        assert isinstance(result, dict)
        assert result["position"] == "absolute"
        assert result["left"] == "100px"
        assert result["top"] == "200px"
        assert result["width"] == "150px"
        assert result["height"] == "80px"

        # 复杂样式解析
        complex_style = "position: absolute; left: 120px; top: 80px; width: 720px; height: 97px; transform: rotate(0deg); color: #333; line-height: 1.0;"
        result = parse_inline_style(complex_style)

        assert result["position"] == "absolute"
        assert result["transform"] == "rotate(0deg)"
        assert result["color"] == "#333"
        assert result["line-height"] == "1.0"

        # 空样式处理
        assert parse_inline_style("") == {}
        assert parse_inline_style(None) == {}

    def test_parse_px_value_function(self):
        """测试px值解析函数"""
        # 标准px值
        assert parse_px_value("100px") == 100.0
        assert parse_px_value("0px") == 0.0
        assert parse_px_value("50.5px") == 50.5

        # 无px后缀
        assert parse_px_value("200") == 200.0
        assert parse_px_value("0") == 0.0

        # 带默认值
        assert parse_px_value("", 100.0) == 100.0
        assert parse_px_value("auto", 50.0) == 50.0
        assert parse_px_value("invalid", 0.0) == 0.0

    def test_parse_radius_value_function(self):
        """测试圆角值解析函数"""
        # 单个值
        assert parse_radius_value("10px") == 10.0
        assert parse_radius_value("0px") == 0.0

        # 多个值（取第一个）
        assert parse_radius_value("10px 20px") == 10.0
        assert parse_radius_value("5px 10px 15px 20px") == 5.0

        # 无效值
        assert parse_radius_value("") is None
        assert parse_radius_value("invalid") is None
        assert parse_radius_value("auto") is None

    def test_complex_css_parsing(self):
        """测试复杂CSS样式解析"""
        # 渐变背景
        gradient_style = "background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%);"
        result = parse_inline_style(gradient_style)
        assert "background" in result
        assert "gradient" in result["background"]

        # 多重变换
        transform_style = "transform: rotate(15deg) scale(1.2) translate(10px, 20px);"
        result = parse_inline_style(transform_style)
        assert result["transform"] == "rotate(15deg) scale(1.2) translate(10px, 20px)"

        # 复杂阴影
        shadow_style = "box-shadow: 0px 10px 20px rgba(0,0,0,0.08), inset 0px 2px 4px rgba(255,255,255,0.5);"
        result = parse_inline_style(shadow_style)
        assert "box-shadow" in result
        assert "rgba(0,0,0,0.08)" in result["box-shadow"]

    def test_edge_cases(self):
        """测试边界情况"""
        # 样式值中的空格和引号
        style_with_quotes = 'font-family: "Arial", sans-serif; font-size: 16px;'
        result = parse_inline_style(style_with_quotes)
        assert result["font-family"] == '"Arial", sans-serif'
        assert result["font-size"] == "16px"

        # 分号缺失
        style_missing_semicolon = "left: 100px top: 200px"
        result = parse_inline_style(style_missing_semicolon)
        # 应该尽力解析，但可能不完整
        assert "left" in result or "top" in result

        # 特殊字符
        style_special_chars = "content: 'Hello: World'; padding: 10px;"
        result = parse_inline_style(style_special_chars)
        assert result["content"] == "'Hello: World'"
        assert result["padding"] == "10px"