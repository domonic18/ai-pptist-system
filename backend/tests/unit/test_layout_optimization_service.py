"""
布局优化Service单元测试
测试HTML生成和解析流程
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.layout.layout_optimization_service import LayoutOptimizationService
from app.schemas.layout_optimization import ElementData, CanvasSize, OptimizationOptions


class TestLayoutOptimizationService:
    """布局优化Service测试类"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建Service实例"""
        service = LayoutOptimizationService(mock_db)
        # 模拟AI客户端
        service.ai_client = AsyncMock()
        return service

    def test_convert_to_html_text_element(self, service):
        """测试文本元素转换为HTML"""
        element = ElementData(
            id="text_001",
            type="text",
            left=100,
            top=50,
            width=600,
            height=80,
            rotate=0,
            content="测试标题",
            defaultFontName="Microsoft YaHei",
            defaultColor="#333333",
            lineHeight=1.5
        )

        html = service._element_to_html_text(element)

        # 验证HTML结构
        assert 'data-id="text_001"' in html
        assert 'data-type="text"' in html
        assert 'class="ppt-element ppt-text"' in html
        assert '测试标题' in html
        assert 'left: 100px' in html
        assert 'top: 50px' in html
        assert 'font-family: \'Microsoft YaHei\'' in html
        assert 'color: #333333' in html

    def test_convert_to_html_shape_element(self, service):
        """测试形状元素转换为HTML"""
        element = ElementData(
            id="shape_001",
            type="shape",
            left=100,
            top=150,
            width=760,
            height=300,
            rotate=0,
            fill="#f5f5f5",
            outline={"color": "#ddd", "width": 2},
            text={"content": "形状内容"}
        )

        html = service._element_to_html_shape(element)

        # 验证HTML结构
        assert 'data-id="shape_001"' in html
        assert 'data-type="shape"' in html
        assert 'class="ppt-element ppt-shape"' in html
        assert 'background-color: #f5f5f5' in html
        assert 'border: 2px solid #ddd' in html
        assert '形状内容' in html

    def test_convert_to_html_image_element(self, service):
        """测试图片元素转换为HTML"""
        element = ElementData(
            id="image_001",
            type="image",
            left=50,
            top=200,
            width=200,
            height=150,
            rotate=0,
            src="https://example.com/image.jpg",
            fixedRatio=True
        )

        html = service._element_to_html_image(element)

        # 验证HTML结构
        assert 'data-id="image_001"' in html
        assert 'data-type="image"' in html
        assert 'class="ppt-element ppt-image"' in html
        assert 'src="https://example.com/image.jpg"' in html
        assert 'left: 50px' in html
        assert 'top: 200px' in html
        assert 'object-fit: cover' in html

    def test_convert_to_html_full_canvas(self, service):
        """测试完整画布HTML转换"""
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="测试标题"
            ),
            ElementData(
                id="shape_001",
                type="shape",
                left=100,
                top=150,
                width=760,
                height=300,
                fill="#f5f5f5",
                text="形状内容"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        html = service._convert_to_html(elements, canvas_size)

        # 验证画布结构
        assert 'class="ppt-canvas"' in html
        assert 'width: 1000px' in html
        assert 'height: 562.5px' in html
        assert 'background: white' in html

        # 验证元素数量
        assert html.count('class="ppt-element"') == 2
        assert '测试标题' in html
        assert '形状内容' in html

    def test_build_requirements_with_options(self, service):
        """测试构建优化要求（带选项）"""
        options = OptimizationOptions(
            keep_colors=True,
            keep_fonts=True,
            style="professional"
        )

        requirements = service._build_requirements(options)

        assert "- 保持原有颜色方案，不得更改元素颜色" in requirements
        assert "- 保持原有字体，不得更改font-family" in requirements
        assert "- 优化风格：专业、商务、简洁" in requirements

    def test_build_requirements_without_options(self, service):
        """测试构建优化要求（无选项）"""
        requirements = service._build_requirements(None)

        assert "- 全面优化布局、字体大小、颜色、间距" in requirements

    def test_extract_html_from_response(self, service):
        """测试从LLM响应中提取HTML"""
        # 模拟LLM响应（包含markdown代码块）
        llm_response = """
        这是LLM的响应，包含优化后的HTML：

        ```html
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="text_001" data-type="text" style="position: absolute; left: 150px; top: 80px; width: 700px; height: 100px;">
            优化后的标题
          </div>
        </div>
        ```

        优化说明：调整了标题位置和大小。
        """

        extracted_html = service._extract_html_from_response(llm_response)

        # 验证提取的HTML
        assert 'class="ppt-canvas"' in extracted_html
        assert 'data-id="text_001"' in extracted_html
        assert '优化后的标题' in extracted_html
        assert not extracted_html.startswith('```html')
        assert not extracted_html.endswith('```')

    def test_parse_inline_style(self, service):
        """测试解析内联样式"""
        style_str = "position: absolute; left: 100px; top: 50px; color: #333"

        style_dict = service._parse_inline_style(style_str)

        assert style_dict["position"] == "absolute"
        assert style_dict["left"] == "100px"
        assert style_dict["top"] == "50px"
        assert style_dict["color"] == "#333"

    def test_parse_px_value(self, service):
        """测试解析px值"""
        assert service._parse_px_value("100px") == 100.0
        assert service._parse_px_value("50.5px") == 50.5
        assert service._parse_px_value("100") == 100.0
        assert service._parse_px_value("") == 0.0
        assert service._parse_px_value("invalid") == 0.0

    def test_parse_rotate_value(self, service):
        """测试解析旋转角度"""
        assert service._parse_rotate_value("rotate(15deg)") == 15.0
        assert service._parse_rotate_value("rotate(-45deg)") == -45.0
        assert service._parse_rotate_value("rotate(0deg)") == 0.0
        assert service._parse_rotate_value("") == 0.0
        assert service._parse_rotate_value("invalid") == 0.0

    @pytest.mark.asyncio
    async def test_optimize_layout_success(self, service):
        """测试完整的布局优化流程"""
        # 模拟元素
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="测试标题"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        # 模拟LLM响应
        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="text_001" data-type="text" style="position: absolute; left: 150px; top: 80px; width: 700px; height: 100px; font-size: 42px; font-weight: bold;">
            测试标题
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size
        )

        # 验证结果
        assert len(result) == 1
        assert result[0].id == "text_001"
        assert result[0].content == "测试标题"  # 内容保持不变
        assert result[0].left == 150.0  # 位置已优化
        assert result[0].top == 80.0
        assert result[0].width == 700.0
        assert result[0].height == 100.0

    @pytest.mark.asyncio
    async def test_optimize_layout_validation_failure(self, service):
        """测试布局优化验证失败"""
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="测试标题"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        # 模拟LLM返回无效HTML（缺少元素）
        invalid_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <!-- 缺少text_001元素 -->
        </div>
        """

        service.ai_client.ai_call.return_value = invalid_html

        # 验证会抛出异常
        with pytest.raises(ValueError):
            await service.optimize_layout(
                slide_id="slide_001",
                elements=elements,
                canvas_size=canvas_size
            )