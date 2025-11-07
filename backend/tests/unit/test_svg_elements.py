"""
SVG元素解析单元测试
测试SVG元素的解析、转换和渲染功能
"""

import pytest
from app.core.html.html_parser import HTMLParser
from app.schemas.layout_optimization import ElementData


class TestSVGElements:
    """SVG元素测试类"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.parser = HTMLParser()

    def test_parse_svg_with_single_path(self):
        """测试解析包含单个path的SVG元素"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-1" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z" stroke="#FBD26A" stroke-width="2"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-1",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-1"
        assert element.type == "shape"
        assert element.left == 100.0
        assert element.top == 100.0
        assert element.width == 40.0
        assert element.height == 40.0
        assert element.viewBox == [24.0, 24.0]
        assert "M12 2L20 7V17L12 22L4 17V7L12 2Z" in element.path
        assert element.fill == '#ffffff'

    def test_parse_svg_with_multiple_paths(self):
        """测试解析包含多个path的SVG元素（应使用第一个path）"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-2" style="position: absolute; left: 200px; top: 200px; width: 50px; height: 50px;" viewBox="0 0 100 100">
                <path d="M10 10L90 10L90 90L10 90Z" fill="blue"/>
                <path d="M20 20L80 20L80 80L20 80Z" fill="red"/>
                <path d="M30 30L70 30L70 70L30 70Z" fill="green"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-2",
                type="shape",
                left=0,
                top=0,
                width=50,
                height=50,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-2"
        assert element.type == "shape"
        # 应该使用第一个path
        assert "M10 10L90 10L90 90L10 90Z" in element.path
        assert element.viewBox == [100.0, 100.0]

    def test_parse_svg_without_path(self):
        """测试解析没有path的SVG元素（应生成默认矩形）"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-3" style="position: absolute; left: 50px; top: 50px; width: 30px; height: 30px;" viewBox="0 0 24 24">
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-3",
                type="shape",
                left=0,
                top=0,
                width=30,
                height=30,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-3"
        assert element.type == "shape"
        assert element.left == 50.0
        assert element.top == 50.0
        assert element.width == 30.0
        assert element.height == 30.0
        assert element.viewBox == [24.0, 24.0]
        # 应该生成默认矩形路径
        assert element.path is not None
        assert "M 0 0" in element.path

    def test_parse_svg_without_viewbox(self):
        """测试解析没有viewBox的SVG元素（应使用元素尺寸）"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-4" style="position: absolute; left: 150px; top: 150px; width: 60px; height: 60px;" fill="none">
                <path d="M5 5L55 5L55 55L5 55Z" stroke="black"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-4",
                type="shape",
                left=0,
                top=0,
                width=60,
                height=60,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-4"
        assert element.type == "shape"
        # 没有viewBox时应该使用元素尺寸
        assert element.viewBox == [60.0, 60.0]
        assert element.width == 60.0
        assert element.height == 60.0

    def test_parse_svg_with_different_viewbox_formats(self):
        """测试解析不同viewBox格式的SVG元素"""
        test_cases = [
            ("0 0 24 24", [24.0, 24.0]),
            ("0 0 100 100", [100.0, 100.0]),
            ("10 10 50 50", [50.0, 50.0]),
            ("0 0 200 150", [200.0, 150.0]),
        ]

        for viewbox_str, expected_viewbox in test_cases:
            html_content = f'''
            <div class="ppt-canvas">
                <svg class="ppt-element" data-id="svg-test" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="{viewbox_str}">
                    <path d="M0 0L10 0L10 10L0 10Z"/>
                </svg>
            </div>
            '''
            original_elements = [
                ElementData(
                    id="svg-test",
                    type="shape",
                    left=0,
                    top=0,
                    width=40,
                    height=40,
                    fill="#ffffff",
                    text={"content": ""}
                )
            ]

            elements = self.parser.parse_html_to_elements(html_content, original_elements)
            assert len(elements) == 1
            element = elements[0]
            assert element.viewBox == expected_viewbox, \
                f"Expected viewBox {expected_viewbox} for viewBox '{viewbox_str}', got {element.viewBox}"

    def test_parse_svg_with_rotation(self):
        """测试解析带旋转的SVG元素"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-5" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px; transform: rotate(45deg);" viewBox="0 0 24 24">
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-5",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-5"
        assert element.type == "shape"
        assert element.rotate == 45.0

    def test_parse_svg_with_complex_path(self):
        """测试解析复杂path的SVG元素"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-6" style="position: absolute; left: 100px; top: 100px; width: 100px; height: 100px;" viewBox="0 0 100 100">
                <path d="M10 10 Q20 20 30 10 T50 10 Q60 20 70 10 T90 10 L90 90 Q80 80 70 90 T50 90 Q40 80 30 90 T10 90 Z" fill="blue"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-6",
                type="shape",
                left=0,
                top=0,
                width=100,
                height=100,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-6"
        assert element.type == "shape"
        # 复杂path应该被正确保留
        assert "Q20 20 30 10" in element.path
        assert "T50 10" in element.path
        assert element.viewBox == [100.0, 100.0]

    def test_parse_svg_with_viewbox_lowercase(self):
        """测试解析viewBox属性为小写的SVG（BeautifulSoup会将属性名转为小写）"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-7" style="position: absolute; left: 100px; top: 100px; width: 50px; height: 50px;" viewbox="0 0 30 30">
                <path d="M0 0L15 0L15 15L0 15Z"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-7",
                type="shape",
                left=0,
                top=0,
                width=50,
                height=50,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-7"
        assert element.type == "shape"
        # 应该正确解析小写的viewbox
        assert element.viewBox == [30.0, 30.0]

    def test_parse_svg_without_data_id(self):
        """测试解析没有data-id的SVG元素（应该生成新ID）"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="0 0 24 24">
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="dummy-id",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        # 解析器会为没有ID的元素生成ID
        assert len(elements) >= 1
        # 找到新生成的SVG元素
        svg_elements = [e for e in elements if e.type == "shape" and e.left == 100.0]
        assert len(svg_elements) == 1

    def test_parse_svg_maintains_original_properties(self):
        """测试SVG解析保持原始属性"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-8" style="position: absolute; left: 120px; top: 130px; width: 45px; height: 55px; transform: rotate(30deg);" viewBox="0 0 24 24">
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z" fill="gold" stroke="darkgoldenrod" stroke-width="1.5"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-8",
                type="shape",
                left=0,
                top=0,
                width=45,
                height=55,
                rotate=30.0,
                fill="gold",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-8"
        assert element.type == "shape"
        assert element.left == 120.0
        assert element.top == 130.0
        assert element.width == 45.0
        assert element.height == 55.0
        assert element.rotate == 30.0
        assert element.fill == "gold"
        assert element.viewBox == [24.0, 24.0]

    def test_parse_svg_with_empty_path_attributes(self):
        """测试解析带有空path属性的SVG元素"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-9" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="0 0 24 24">
                <path d="" stroke="red"/>
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z"/>
                <path fill="blue"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-9",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-9"
        # 应该使用第一个有效的path（第二个path）
        assert "M12 2L20 7V17L12 22L4 17V7L12 2Z" in element.path

    def test_parse_multiple_svg_elements(self):
        """测试解析多个SVG元素"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-a" style="position: absolute; left: 50px; top: 50px; width: 30px; height: 30px;" viewBox="0 0 20 20">
                <path d="M0 0L10 0L10 10L0 10Z" fill="red"/>
            </svg>
            <svg class="ppt-element" data-id="svg-b" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="0 0 30 30">
                <path d="M0 0L15 0L15 15L0 15Z" fill="blue"/>
            </svg>
            <svg class="ppt-element" data-id="svg-c" style="position: absolute; left: 150px; top: 150px; width: 50px; height: 50px;" viewBox="0 0 40 40">
                <path d="M0 0L20 0L20 20L0 20Z" fill="green"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-a",
                type="shape",
                left=0,
                top=0,
                width=30,
                height=30,
                fill="#ffffff",
                text={"content": ""}
            ),
            ElementData(
                id="svg-b",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            ),
            ElementData(
                id="svg-c",
                type="shape",
                left=0,
                top=0,
                width=50,
                height=50,
                fill="#ffffff",
                text={"content": ""}
            ),
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 3

        # 验证第一个SVG
        svg_a = next((e for e in elements if e.id == "svg-a"), None)
        assert svg_a is not None
        assert svg_a.viewBox == [20.0, 20.0]
        assert svg_a.left == 50.0
        assert svg_a.top == 50.0

        # 验证第二个SVG
        svg_b = next((e for e in elements if e.id == "svg-b"), None)
        assert svg_b is not None
        assert svg_b.viewBox == [30.0, 30.0]
        assert svg_b.left == 100.0
        assert svg_b.top == 100.0

        # 验证第三个SVG
        svg_c = next((e for e in elements if e.id == "svg-c"), None)
        assert svg_c is not None
        assert svg_c.viewBox == [40.0, 40.0]
        assert svg_c.left == 150.0
        assert svg_c.top == 150.0

    def test_parse_svg_with_viewbox_decimal_values(self):
        """测试解析带有小数值的viewBox"""
        html_content = '''
        <div class="ppt-canvas">
            <svg class="ppt-element" data-id="svg-10" style="position: absolute; left: 100px; top: 100px; width: 40px; height: 40px;" viewBox="0.0 0.0 24.5 24.5">
                <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z"/>
            </svg>
        </div>
        '''
        original_elements = [
            ElementData(
                id="svg-10",
                type="shape",
                left=0,
                top=0,
                width=40,
                height=40,
                fill="#ffffff",
                text={"content": ""}
            )
        ]

        elements = self.parser.parse_html_to_elements(html_content, original_elements)

        assert len(elements) == 1
        element = elements[0]
        assert element.id == "svg-10"
        # 应该正确解析小数值
        assert element.viewBox == [24.5, 24.5]
