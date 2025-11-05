"""
HTML转换器单元测试
测试PPTist元素到HTML的转换功能
"""

import pytest
from app.core.html import HTMLConverter
from app.schemas.layout_optimization import ElementData, CanvasSize


class TestHTMLConverter:
    """HTML转换器测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.converter = HTMLConverter()
    
    def test_convert_text_element(self):
        """测试转换文本元素"""
        element = ElementData(
            id="test-text-1",
            type="text",
            left=100.0,
            top=50.0,
            width=300.0,
            height=60.0,
            rotate=0.0,
            content="测试文本",
            defaultFontName="微软雅黑",
            defaultColor="#333",
            lineHeight=1.5
        )
        
        html = self.converter._convert_text_element(element)
        
        # 验证HTML结构
        assert 'class="ppt-element ppt-text"' in html
        assert 'data-id="test-text-1"' in html
        assert 'data-type="text"' in html
        assert 'left: 100px' in html
        assert 'top: 50px' in html
        assert 'width: 300px' in html
        assert 'height: 60px' in html
        assert 'transform: rotate(0deg)' in html
        assert "font-family: '微软雅黑'" in html
        assert 'color: #333' in html
        assert 'line-height: 1.5' in html
        assert '测试文本' in html
    
    def test_convert_shape_element(self):
        """测试转换形状元素"""
        element = ElementData(
            id="test-shape-1",
            type="shape",
            left=200.0,
            top=100.0,
            width=400.0,
            height=200.0,
            rotate=0.0,
            fill="#5b9bd5",
            outline={"color": "#000", "width": 2},
            text={"content": "形状文字"}
        )
        
        html = self.converter._convert_shape_element(element)
        
        # 验证HTML结构
        assert 'class="ppt-element ppt-shape"' in html
        assert 'data-id="test-shape-1"' in html
        assert 'data-type="shape"' in html
        assert 'left: 200px' in html
        assert 'top: 100px' in html
        assert 'width: 400px' in html
        assert 'height: 200px' in html
        assert 'background: #5b9bd5' in html
        assert 'border: 2px solid #000' in html
        assert 'class="shape-text"' in html
        assert '形状文字' in html
    
    def test_convert_line_element(self):
        """测试转换线条元素"""
        element = ElementData(
            id="test-line-1",
            type="line",
            left=150.0,
            top=75.0,
            width=1.0,
            height=1.0,
            rotate=0.0
        )
        
        html = self.converter._convert_line_element(element)
        
        # 验证HTML结构
        assert 'class="ppt-element ppt-line"' in html
        assert 'data-id="test-line-1"' in html
        assert 'data-type="line"' in html
        assert 'left: 150px' in html
        assert 'top: 75px' in html
        assert 'width: 1px' in html
        assert 'height: 1px' in html
        # 不再包含限制注释
        assert '<!-- 线条元素暂不优化 -->' not in html
    
    def test_convert_image_element(self):
        """测试转换图片元素"""
        element = ElementData(
            id="test-image-1",
            type="image",
            left=300.0,
            top=150.0,
            width=500.0,
            height=300.0,
            rotate=0.0,
            src="https://example.com/image.jpg",
            fixedRatio=True
        )
        
        html = self.converter._convert_image_element(element)
        
        # 验证HTML结构
        assert 'class="ppt-element ppt-image"' in html
        assert 'data-id="test-image-1"' in html
        assert 'data-type="image"' in html
        assert 'left: 300px' in html
        assert 'top: 150px' in html
        assert 'width: 500px' in html
        assert 'height: 300px' in html
        assert 'src="https://example.com/image.jpg"' in html
    
    def test_convert_to_html_with_multiple_elements(self):
        """测试转换多个元素为完整HTML"""
        canvas_size = CanvasSize(width=1000.0, height=562.5)
        
        elements = [
            ElementData(
                id="ptNnUJ",
                type="text",
                left=145.0,
                top=148.0,
                width=711.0,
                height=77.0,
                rotate=0.0,
                content="在此处添加标题",
                defaultColor="#333",
                lineHeight=1.2
            ),
            ElementData(
                id="mRHvQN",
                type="text",
                left=207.0,
                top=249.0,
                width=585.0,
                height=56.0,
                rotate=0.0,
                content="在此处添加副标题",
                defaultColor="#333"
            ),
            ElementData(
                id="7CQDwc",
                type="line",
                left=323.0,
                top=238.0,
                width=1.0,
                height=1.0,
                rotate=0.0
            ),
            ElementData(
                id="09wqWw",
                type="shape",
                left=-27.0,
                top=432.0,
                width=1056.0,
                height=162.0,
                rotate=0.0,
                fill="#5b9bd5",
                text={"content": ""}
            )
        ]
        
        html = self.converter.convert_to_html(elements, canvas_size)
        
        # 验证HTML结构
        assert '<div class="ppt-canvas"' in html
        assert 'width: 1000.0px' in html
        assert 'height: 562.5px' in html
        
        # 验证所有元素都被包含
        assert 'data-id="ptNnUJ"' in html
        assert 'data-id="mRHvQN"' in html
        assert 'data-id="7CQDwc"' in html
        assert 'data-id="09wqWw"' in html
        
        # 验证内容
        assert '在此处添加标题' in html
        assert '在此处添加副标题' in html
        
        # 验证HTML结构完整性
        assert html.startswith('<div class="ppt-canvas"')
        assert html.endswith('</div>')
    
    def test_convert_element_with_rotation(self):
        """测试转换带旋转的元素"""
        element = ElementData(
            id="rotated-text",
            type="text",
            left=100.0,
            top=100.0,
            width=200.0,
            height=50.0,
            rotate=45.0,
            content="旋转文本"
        )
        
        html = self.converter._convert_text_element(element)
        
        assert 'transform: rotate(45deg)' in html
    
    def test_convert_shape_with_dict_text(self):
        """测试转换带字典格式文字的形状"""
        element = ElementData(
            id="shape-with-text",
            type="shape",
            left=100.0,
            top=100.0,
            width=200.0,
            height=100.0,
            rotate=0.0,
            fill="#ff0000",
            text={"content": "字典格式文字"}
        )
        
        html = self.converter._convert_shape_element(element)
        
        assert '字典格式文字' in html
    
    def test_convert_shape_with_dict_outline(self):
        """测试转换带字典格式outline的形状"""
        element = ElementData(
            id="shape-outline",
            type="shape",
            left=100.0,
            top=100.0,
            width=200.0,
            height=100.0,
            rotate=0.0,
            fill="#00ff00",
            outline={"color": "#0000ff", "width": 3}
        )
        
        html = self.converter._convert_shape_element(element)
        
        assert 'border: 3px solid #0000ff' in html
    
    def test_convert_shape_with_shadow_and_opacity(self):
        """测试转换带阴影和透明度的形状元素"""
        element = ElementData(
            id="test-shape-2",
            type="shape",
            left=100.0,
            top=50.0,
            width=300.0,
            height=150.0,
            rotate=0.0,
            fill="#ff0000",
            shadow={"color": "#000000", "h": 5, "v": 5, "blur": 10, "spread": 2},
            opacity=0.8
        )

        html = self.converter._convert_shape_element(element)

        # 验证HTML结构
        assert 'class="ppt-element ppt-shape"' in html
        assert 'data-id="test-shape-2"' in html
        assert 'background: #ff0000' in html
        assert 'box-shadow: #000000 5px 5px 10px 2px' in html
        assert 'opacity: 0.8' in html

    def test_convert_text_with_advanced_styles(self):
        """测试转换带高级样式的文本元素"""
        element = ElementData(
            id="test-text-2",
            type="text",
            left=150.0,
            top=75.0,
            width=400.0,
            height=80.0,
            rotate=0.0,
            content="高级样式文本",
            defaultFontName="Arial",
            defaultColor="#333333",
            fontSize=24.0,
            fontWeight="bold",
            textAlign="center",
            wordSpace=2.0,
            paragraphSpace=10.0,
            fill="#f0f0f0"
        )

        html = self.converter._convert_text_element(element)

        # 验证HTML结构
        assert 'class="ppt-element ppt-text"' in html
        assert 'data-id="test-text-2"' in html
        assert "font-family: 'Arial'" in html
        assert 'color: #333333' in html
        assert 'font-size: 24px' in html
        assert 'font-weight: bold' in html
        assert 'text-align: center' in html
        assert 'letter-spacing: 2.0px' in html
        assert 'margin-bottom: 10.0px' in html
        assert 'background: #f0f0f0' in html
        assert '高级样式文本' in html

    def test_convert_image_with_filter_and_shadow(self):
        """测试转换带滤镜和阴影的图片元素"""
        element = ElementData(
            id="test-image-2",
            type="image",
            left=200.0,
            top=100.0,
            width=500.0,
            height=300.0,
            rotate=0.0,
            src="https://example.com/image.jpg",
            radius=15.0,
            shadow={"color": "rgba(0,0,0,0.5)", "h": 0, "v": 4, "blur": 8, "spread": 0},
            filter={"brightness": 120, "contrast": 110, "saturation": 90}
        )

        html = self.converter._convert_image_element(element)

        # 验证HTML结构
        assert 'class="ppt-element ppt-image"' in html
        assert 'data-id="test-image-2"' in html
        assert 'border-radius: 15px' in html
        assert 'box-shadow: rgba(0,0,0,0.5) 0px 4px 8px 0px' in html
        assert 'filter: brightness(120%) contrast(110%) saturate(90%)' in html
        assert 'src="https://example.com/image.jpg"' in html

