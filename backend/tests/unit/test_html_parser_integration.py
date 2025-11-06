#!/usr/bin/env python3
"""
HTML解析器集成单元测试
模拟真实LLM响应场景，测试完整的HTML解析流程
遵循项目测试规范：快速执行，无外部依赖
"""

import pytest
from app.core.html import HTMLParser
from app.schemas.layout_optimization import ElementData


@pytest.mark.unit
@pytest.mark.html_parser
@pytest.mark.integration
class TestHTMLParserIntegration:
    """HTML解析器集成测试类"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.parser = HTMLParser()

    def test_parse_realistic_llm_response(self):
        """测试解析真实LLM响应场景"""
        # 模拟真实LLM生成的HTML内容
        realistic_html = '''
        <div class="ppt-canvas" style="width: 1920px; height: 1080px; position: relative; background: linear-gradient(135deg, #f5f7fa 0%, #e4eaf5 100%);">

            <!-- 标题元素 -->
            <div class="ppt-element ppt-text"
                 data-id="title-element"
                 data-type="text"
                 style="position: absolute; left: 120px; top: 80px; width: 720px; height: 97px; transform: rotate(0deg); color: #100F0D; line-height: 1.0;">
                <p style="text-align: left;"><span style="color: #100F0D; font-size: 75.9px; font-family: 微软雅黑; font-weight: bold;">分类是第一步</span></p>
            </div>

            <!-- 装饰形状 -->
            <div class="ppt-element ppt-shape"
                 data-id="decoration-shape"
                 data-type="shape"
                 style="position: absolute; left: 80px; top: 460px; width: 60px; height: 60px; transform: rotate(0deg); background: rgba(255, 203, 0, 0.2); border-radius: 30px;">
            </div>

            <!-- 内容卡片 -->
            <div class="ppt-element ppt-shape"
                 data-id="content-card"
                 data-type="shape"
                 style="position: absolute; left: 120px; top: 580px; width: 550px; height: 380px; transform: rotate(0deg); background: white; border-radius: 16px; box-shadow: 0px 10px 20px rgba(0,0,0,0.08);">
            </div>
        </div>
        '''

        # 原始元素列表（模拟PPT中的现有元素）
        original_elements = [
            ElementData(
                id="existing-slide",
                type="shape",
                left=0.0,
                top=0.0,
                width=1920.0,
                height=1080.0,
                rotate=0.0,
                content="slide背景"
            )
        ]

        # 解析HTML内容
        optimized_elements = self.parser.parse_html_to_elements(
            realistic_html,
            original_elements
        )

        # 验证解析结果
        assert len(optimized_elements) >= 3  # 至少包含3个新元素

        # 验证元素类型和基本属性
        element_types = {el.type for el in optimized_elements}
        assert "text" in element_types
        assert "shape" in element_types

        # 验证标题元素
        title_element = next((el for el in optimized_elements if el.id == "title-element"), None)
        assert title_element is not None
        assert title_element.type == "text"
        assert title_element.left == 120.0
        assert title_element.top == 80.0

        # 验证装饰形状
        decoration_element = next((el for el in optimized_elements if el.id == "decoration-shape"), None)
        assert decoration_element is not None
        assert decoration_element.type == "shape"
        assert decoration_element.width == 60.0
        assert decoration_element.height == 60.0

        # 验证内容卡片
        card_element = next((el for el in optimized_elements if el.id == "content-card"), None)
        assert card_element is not None
        assert card_element.type == "shape"
        assert card_element.left == 120.0
        assert card_element.top == 580.0
        assert card_element.width == 550.0
        assert card_element.height == 380.0

    def test_parse_mixed_element_types(self):
        """测试解析混合元素类型"""
        mixed_html = '''
        <div class="ppt-canvas" style="width: 1920px; height: 1080px; position: relative; background: white;">

            <!-- 文本元素 -->
            <div class="ppt-element ppt-text"
                 data-id="text-1"
                 data-type="text"
                 style="position: absolute; left: 100px; top: 100px; width: 300px; height: 50px;">
                <h2>标题文本</h2>
            </div>

            <!-- 形状元素 -->
            <div class="ppt-element ppt-shape"
                 data-id="shape-1"
                 data-type="shape"
                 style="position: absolute; left: 100px; top: 200px; width: 200px; height: 100px; background: #FF6B6B;">
            </div>

            <!-- 图片元素 -->
            <div class="ppt-element ppt-image"
                 data-id="image-1"
                 data-type="image"
                 style="position: absolute; left: 400px; top: 200px; width: 300px; height: 200px;">
                <img src="https://example.com/image.jpg" alt="示例图片">
            </div>

        </div>
        '''

        original_elements = [
            ElementData(
                id="slide-bg",
                type="shape",
                left=0.0,
                top=0.0,
                width=1920.0,
                height=1080.0,
                rotate=0.0
            )
        ]

        optimized_elements = self.parser.parse_html_to_elements(
            mixed_html,
            original_elements
        )

        # 验证元素数量和类型
        assert len(optimized_elements) >= 3

        # 验证各种元素类型都被正确解析
        element_ids = {el.id for el in optimized_elements}
        assert "text-1" in element_ids
        assert "shape-1" in element_ids
        assert "image-1" in element_ids

        # 验证各元素的基本属性
        for element_id in ["text-1", "shape-1", "image-1"]:
            element = next(el for el in optimized_elements if el.id == element_id)
            assert element.type in ["text", "shape", "image"]
            assert element.left is not None
            assert element.top is not None
            assert element.width is not None
            assert element.height is not None

    def test_parse_empty_and_invalid_elements(self):
        """测试解析空元素和无效元素"""
        # 包含空元素的HTML
        html_with_empty = '''
        <div class="ppt-canvas" style="width: 1920px; height: 1080px; position: relative; background: white;">

            <!-- 有效元素 -->
            <div class="ppt-element ppt-shape"
                 data-id="valid-element"
                 data-type="shape"
                 style="position: absolute; left: 100px; top: 100px; width: 100px; height: 100px; background: #4CAF50;">
            </div>

            <!-- 空元素 -->
            <div class="ppt-element ppt-shape"
                 data-id="empty-element"
                 data-type="shape"
                 style="position: absolute; left: 200px; top: 100px; width: 0px; height: 0px;">
            </div>

            <!-- 无效样式元素 -->
            <div class="ppt-element ppt-text"
                 data-id="invalid-style-element"
                 data-type="text"
                 style="position: absolute; left: invalid; top: 100px; width: 100px; height: 50px;">
                无效样式文本
            </div>

        </div>
        '''

        original_elements = [
            ElementData(
                id="base-element",
                type="shape",
                left=0.0,
                top=0.0,
                width=1920.0,
                height=1080.0,
                rotate=0.0
            )
        ]

        optimized_elements = self.parser.parse_html_to_elements(
            html_with_empty,
            original_elements
        )

        # 验证至少有效元素被解析
        assert len(optimized_elements) >= 1

        # 验证有效元素存在
        valid_element = next((el for el in optimized_elements if el.id == "valid-element"), None)
        assert valid_element is not None
        assert valid_element.type == "shape"

    def test_parse_elements_with_special_characters(self):
        """测试解析包含特殊字符的元素"""
        special_char_html = '''
        <div class="ppt-canvas" style="width: 1920px; height: 1080px; position: relative; background: white;">

            <!-- 包含中文的文本 -->
            <div class="ppt-element ppt-text"
                 data-id="chinese-text"
                 data-type="text"
                 style="position: absolute; left: 100px; top: 100px; width: 300px; height: 50px; color: #333;">
                这是一个包含中文的文本内容
            </div>

            <!-- 包含特殊符号的文本 -->
            <div class="ppt-element ppt-text"
                 data-id="special-chars-text"
                 data-type="text"
                 style="position: absolute; left: 100px; top: 200px; width: 400px; height: 50px;">
                Special characters: @#$%^&*()_+-={}[]|\\:";'<>?,./
            </div>

            <!-- 包含HTML实体的文本 -->
            <div class="ppt-element ppt-text"
                 data-id="html-entities-text"
                 data-type="text"
                 style="position: absolute; left: 100px; top: 300px; width: 300px; height: 50px;">
                HTML entities: &lt;&gt;&amp;&quot;&#39;
            </div>

        </div>
        '''

        original_elements = [
            ElementData(
                id="base-slide",
                type="shape",
                left=0.0,
                top=0.0,
                width=1920.0,
                height=1080.0,
                rotate=0.0
            )
        ]

        # 解析应该不抛出异常
        optimized_elements = self.parser.parse_html_to_elements(
            special_char_html,
            original_elements
        )

        # 验证元素被正确解析
        assert len(optimized_elements) >= 3

        # 验证包含特殊字符的元素存在
        element_ids = {el.id for el in optimized_elements}
        assert "chinese-text" in element_ids
        assert "special-chars-text" in element_ids
        assert "html-entities-text" in element_ids