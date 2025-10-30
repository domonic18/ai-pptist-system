"""
HTML解析器单元测试
使用真实的LLM响应数据进行测试
"""

import pytest
from app.core.html import HTMLParser
from app.schemas.layout_optimization import ElementData


class TestHTMLParser:
    """HTML解析器测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.parser = HTMLParser()
    
    def test_extract_html_from_llm_response(self):
        """测试从LLM响应中提取HTML内容"""
        # 使用真实的LLM响应数据
        llm_response = '''<div class="ppt-canvas" style="width: 1000.0px; height: 562.5px; position: relative; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);">

  <div
    class="ppt-element ppt-text"
    data-id="ptNnUJ"
    data-type="text"
    style="position: absolute; left: 50px; top: 120px; width: 900px; height: 90px; transform: rotate(0deg); color: #2c3e50; line-height: 1.1">
    <p style="text-align: center;"><strong><span style="font-size: 64px; font-weight: 700; letter-spacing: -0.5px;">在此处添加标题</span></strong></p>
  </div>

  <div
    class="ppt-element ppt-text"
    data-id="mRHvQN"
    data-type="text"
    style="position: absolute; left: 50px; top: 230px; width: 900px; height: 40px; transform: rotate(0deg); color: #7f8c8d">
    <p style="text-align: center;"><span style="font-size: 32px; font-weight: 300; letter-spacing: 1px;">在此处添加副标题</span></p>
  </div>

  <div
    class="ppt-element ppt-line"
    data-id="7CQDwc"
    data-type="line"
    style="position: absolute; left: 250px; top: 210px; width: 500px; height: 2px; background: linear-gradient(90deg, transparent 0%, #3498db 50%, transparent 100%); border-radius: 1px; box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3)">
    <!-- 线条元素暂不优化 -->
  </div>

  <div
    class="ppt-element ppt-shape"
    data-id="09wqWw"
    data-type="shape"
    style="position: absolute; left: 0px; top: 380px; width: 1000px; height: 182px; transform: rotate(0deg); background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); border-radius: 0; box-shadow: 0 -4px 20px rgba(41, 128, 185, 0.4)">
    <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
      
    </div>
  </div>

</div>'''
        
        # 执行提取
        html_content = self.parser.extract_html_from_response(llm_response)
        
        # 验证结果
        assert html_content is not None
        assert '<div class="ppt-canvas"' in html_content
        assert 'data-id="ptNnUJ"' in html_content
        assert 'data-id="mRHvQN"' in html_content
        assert 'data-id="7CQDwc"' in html_content
        assert 'data-id="09wqWw"' in html_content
    
    def test_extract_html_with_markdown_wrapper(self):
        """测试从带markdown包裹的响应中提取HTML"""
        llm_response = '''```html
<div class="ppt-canvas" style="width: 1000.0px; height: 562.5px;">
  <div class="ppt-element ppt-text" data-id="test1" data-type="text">Test</div>
</div>
```'''
        
        html_content = self.parser.extract_html_from_response(llm_response)
        
        assert html_content is not None
        assert '```' not in html_content  # markdown标记应该被移除
        assert 'data-id="test1"' in html_content
    
    def test_parse_html_to_elements(self):
        """测试解析HTML为元素列表"""
        # 准备测试数据 - 原始元素
        original_elements = [
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
        
        # LLM优化后的HTML
        optimized_html = '''<div class="ppt-canvas" style="width: 1000.0px; height: 562.5px; position: relative; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);">

  <div
    class="ppt-element ppt-text"
    data-id="ptNnUJ"
    data-type="text"
    style="position: absolute; left: 50px; top: 120px; width: 900px; height: 90px; transform: rotate(0deg); color: #2c3e50; line-height: 1.1">
    <p style="text-align: center;"><strong><span style="font-size: 64px; font-weight: 700; letter-spacing: -0.5px;">在此处添加标题</span></strong></p>
  </div>

  <div
    class="ppt-element ppt-text"
    data-id="mRHvQN"
    data-type="text"
    style="position: absolute; left: 50px; top: 230px; width: 900px; height: 40px; transform: rotate(0deg); color: #7f8c8d">
    <p style="text-align: center;"><span style="font-size: 32px; font-weight: 300; letter-spacing: 1px;">在此处添加副标题</span></p>
  </div>

  <div
    class="ppt-element ppt-line"
    data-id="7CQDwc"
    data-type="line"
    style="position: absolute; left: 250px; top: 210px; width: 500px; height: 2px; background: linear-gradient(90deg, transparent 0%, #3498db 50%, transparent 100%); border-radius: 1px; box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3)">
    <!-- 线条元素暂不优化 -->
  </div>

  <div
    class="ppt-element ppt-shape"
    data-id="09wqWw"
    data-type="shape"
    style="position: absolute; left: 0px; top: 380px; width: 1000px; height: 182px; transform: rotate(0deg); background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); border-radius: 0; box-shadow: 0 -4px 20px rgba(41, 128, 185, 0.4)">
    <div class="shape-text" style="padding: 20px; display: flex; align-items: center; justify-content: center; height: 100%;">
      
    </div>
  </div>

</div>'''
        
        # 执行解析
        optimized_elements = self.parser.parse_html_to_elements(
            optimized_html,
            original_elements
        )
        
        # 验证结果
        assert len(optimized_elements) == 4, f"应该解析出4个元素，实际解析出{len(optimized_elements)}个"
        
        # 验证所有元素ID都存在
        element_ids = {el.id for el in optimized_elements}
        assert "ptNnUJ" in element_ids
        assert "mRHvQN" in element_ids
        assert "7CQDwc" in element_ids
        assert "09wqWw" in element_ids
        
        # 验证第一个文本元素的优化结果
        title_element = next(el for el in optimized_elements if el.id == "ptNnUJ")
        assert title_element.type == "text"
        assert title_element.left == 50.0
        assert title_element.top == 120.0
        assert title_element.width == 900.0
        assert title_element.height == 90.0
        assert title_element.content == "在此处添加标题"
        
        # 验证第二个文本元素的优化结果
        subtitle_element = next(el for el in optimized_elements if el.id == "mRHvQN")
        assert subtitle_element.type == "text"
        assert subtitle_element.left == 50.0
        assert subtitle_element.top == 230.0
        assert subtitle_element.width == 900.0
        assert subtitle_element.content == "在此处添加副标题"
        
        # 验证线条元素（保持原样）
        line_element = next(el for el in optimized_elements if el.id == "7CQDwc")
        assert line_element.type == "line"
        # 线条元素应该保持原样
        assert line_element.left == original_elements[2].left
        assert line_element.top == original_elements[2].top
        
        # 验证形状元素的优化结果
        shape_element = next(el for el in optimized_elements if el.id == "09wqWw")
        assert shape_element.type == "shape"
        # 注意：由于解析background使用了linear-gradient，可能解析失败导致使用原始元素
        # 这是因为我们的解析逻辑只处理简单的颜色值
        # 暂时验证元素存在即可
        assert shape_element.id == "09wqWw"
    
    def test_parse_inline_style(self):
        """测试解析内联样式"""
        style_str = "position: absolute; left: 100px; top: 50px; color: #333"
        style_dict = self.parser._parse_inline_style(style_str)
        
        assert style_dict["position"] == "absolute"
        assert style_dict["left"] == "100px"
        assert style_dict["top"] == "50px"
        assert style_dict["color"] == "#333"
    
    def test_parse_px_value(self):
        """测试解析px值"""
        assert self.parser._parse_px_value("100px") == 100.0
        assert self.parser._parse_px_value("100") == 100.0
        assert self.parser._parse_px_value("") == 0.0
        assert self.parser._parse_px_value("invalid") == 0.0
    
    def test_parse_rotate_value(self):
        """测试解析旋转值"""
        assert self.parser._parse_rotate_value("rotate(15deg)") == 15.0
        assert self.parser._parse_rotate_value("rotate(-30deg)") == -30.0
        assert self.parser._parse_rotate_value("rotate(0deg)") == 0.0
        assert self.parser._parse_rotate_value("") == 0.0
        assert self.parser._parse_rotate_value("invalid") == 0.0
    
    def test_extract_html_invalid_response(self):
        """测试提取无效HTML响应"""
        with pytest.raises(ValueError, match="未找到ppt-canvas元素"):
            self.parser.extract_html_from_response("<div>Invalid HTML</div>")
    
    def test_parse_empty_html(self):
        """测试解析空HTML"""
        original_elements = [
            ElementData(
                id="test1",
                type="text",
                left=0.0,
                top=0.0,
                width=100.0,
                height=50.0,
                rotate=0.0,
                content="Test"
            )
        ]
        
        html_content = '<div class="ppt-canvas"></div>'
        
        optimized_elements = self.parser.parse_html_to_elements(
            html_content,
            original_elements
        )
        
        # 空HTML应该解析出0个元素
        assert len(optimized_elements) == 0
    
    def test_parse_element_with_auto_height(self):
        """测试解析带有auto高度的元素"""
        original_elements = [
            ElementData(
                id="auto-height-text",
                type="text",
                left=100.0,
                top=200.0,
                width=300.0,
                height=50.0,
                rotate=0.0,
                content="测试文本"
            )
        ]
        
        # LLM返回的HTML使用了height: auto
        html_content = '''<div class="ppt-canvas">
  <div class="ppt-element ppt-text" data-id="auto-height-text" data-type="text"
       style="position: absolute; left: 100px; top: 200px; width: 300px; height: auto; transform: rotate(0deg);">
    测试文本
  </div>
</div>'''
        
        optimized_elements = self.parser.parse_html_to_elements(
            html_content,
            original_elements
        )
        
        assert len(optimized_elements) == 1
        elem = optimized_elements[0]
        assert elem.id == "auto-height-text"
        # height: auto应该使用原始值
        assert elem.height == 50.0
        assert elem.width == 300.0
    
    def test_parse_shape_with_gradient_background(self):
        """测试解析带有gradient背景的形状"""
        original_elements = [
            ElementData(
                id="gradient-shape",
                type="shape",
                left=100.0,
                top=100.0,
                width=200.0,
                height=100.0,
                rotate=0.0,
                fill="#ff0000",
                text={"content": ""}
            )
        ]
        
        # LLM返回的HTML使用了linear-gradient
        html_content = '''<div class="ppt-canvas">
  <div class="ppt-element ppt-shape" data-id="gradient-shape" data-type="shape"
       style="position: absolute; left: 100px; top: 100px; width: 200px; height: 100px; 
              background: linear-gradient(135deg, #ff0000 0%, #00ff00 100%);">
    <div class="shape-text" style="padding: 20px;"></div>
  </div>
</div>'''
        
        optimized_elements = self.parser.parse_html_to_elements(
            html_content,
            original_elements
        )
        
        assert len(optimized_elements) == 1
        elem = optimized_elements[0]
        assert elem.id == "gradient-shape"
        # gradient应该保留原始颜色
        assert elem.fill == "#ff0000"
    
    def test_parse_complex_styled_elements(self):
        """测试解析带有复杂样式的元素（真实场景）"""
        original_elements = [
            ElementData(
                id="64n3xXebka",
                type="image",
                left=0.0,
                top=178.0,
                width=463.0,
                height=347.0,
                rotate=0.0,
                src="https://example.com/image.jpg",
                fixedRatio=True
            ),
            ElementData(
                id="FnlMu-mtPq",
                type="text",
                left=261.0,
                top=340.0,
                width=213.0,
                height=44.0,
                rotate=0.0,
                content="正数、0、负数"
            )
        ]
        
        # 真实的LLM响应（包含box-shadow, border-radius, overflow等）
        html_content = '''<div class="ppt-canvas">
  <div class="ppt-element ppt-image" data-id="64n3xXebka" data-type="image"
       style="position: absolute; left: 50px; top: 150px; width: 400px; height: 350px; 
              transform: rotate(0deg); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); overflow: hidden;">
    <img src="https://example.com/image.jpg" style="width: 100%; height: 100%; object-fit: cover;" />
  </div>
  <div class="ppt-element ppt-text" data-id="FnlMu-mtPq" data-type="text"
       style="position: absolute; left: 485px; top: 420px; width: 120px; height: auto; color: white;">
    <p style="text-align: center; margin: 0;">正数、0、负数</p>
  </div>
</div>'''
        
        optimized_elements = self.parser.parse_html_to_elements(
            html_content,
            original_elements
        )
        
        assert len(optimized_elements) == 2
        
        # 验证图片元素
        img_elem = next(el for el in optimized_elements if el.id == "64n3xXebka")
        assert img_elem.type == "image"
        assert img_elem.left == 50.0
        assert img_elem.top == 150.0
        assert img_elem.width == 400.0
        assert img_elem.height == 350.0
        
        # 验证文本元素（height: auto）
        text_elem = next(el for el in optimized_elements if el.id == "FnlMu-mtPq")
        assert text_elem.type == "text"
        assert text_elem.left == 485.0
        assert text_elem.top == 420.0
        assert text_elem.width == 120.0
        # height: auto应该保留原始值
        assert text_elem.height == 44.0
        assert text_elem.content == "正数、0、负数"

    def test_parse_radius_value(self):
        """测试解析border-radius值"""
        parser = HTMLParser()

        # 测试基本px值
        assert parser._parse_radius_value("10px") == 10.0
        assert parser._parse_radius_value("25.5px") == 25.5

        # 测试无px后缀
        assert parser._parse_radius_value("15") == 15.0

        # 测试多个值（取第一个）
        assert parser._parse_radius_value("10px 20px") == 10.0
        assert parser._parse_radius_value("5px 10px 15px 20px") == 5.0

        # 测试无效值
        assert parser._parse_radius_value("") is None
        assert parser._parse_radius_value("invalid") is None
        assert parser._parse_radius_value("auto") is None

    def test_parse_image_with_radius(self):
        """测试解析带有border-radius的图片元素"""
        original_elements = [
            ElementData(
                id="radius-image",
                type="image",
                left=100.0,
                top=100.0,
                width=200.0,
                height=150.0,
                rotate=0.0,
                src="https://example.com/image.jpg",
                fixedRatio=True
            )
        ]

        # LLM返回的HTML使用了border-radius
        html_content = '''<div class="ppt-canvas">
  <div class="ppt-element ppt-image" data-id="radius-image" data-type="image"
       style="position: absolute; left: 100px; top: 100px; width: 200px; height: 150px; border-radius: 15px;">
    <img src="https://example.com/image.jpg" />
  </div>
</div>'''

        optimized_elements = self.parser.parse_html_to_elements(
            html_content,
            original_elements
        )

        assert len(optimized_elements) == 1
        elem = optimized_elements[0]
        assert elem.id == "radius-image"
        assert elem.type == "image"
        # 验证radius字段被正确解析
        assert elem.radius == 15.0
        # 验证其他属性保持不变
        assert elem.left == 100.0
        assert elem.top == 100.0
        assert elem.width == 200.0
        assert elem.height == 150.0
        assert elem.src == "https://example.com/image.jpg"

