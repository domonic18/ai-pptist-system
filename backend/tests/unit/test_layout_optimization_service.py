"""
布局优化Service单元测试
测试布局优化流程和集成
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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

    def test_build_requirements_with_options(self, service):
        """测试构建优化要求（带选项）"""
        options = OptimizationOptions(
            keep_colors=True,
            keep_fonts=True,
            style="professional"
        )

        requirements = service._build_requirements(options, None)

        assert "- 保持原有颜色方案，不得更改元素颜色" in requirements
        assert "- 保持原有字体，不得更改font-family" in requirements
        assert "- 优化风格：专业、商务、简洁" in requirements

    def test_build_requirements_without_options(self, service):
        """测试构建优化要求（无选项）"""
        requirements = service._build_requirements(None, None)

        assert requirements == "全面优化"

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
    async def test_optimize_layout_with_valid_new_elements(self, service):
        """测试包含有效新元素ID的布局优化"""
        elements = [
            ElementData(
                id="original1",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="原始文本"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        # LLM创建了有效格式的新元素
        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="original1" data-type="text" style="position: absolute; left: 150px; top: 80px; width: 700px; height: 100px;">
            原始文本
          </div>
          <div class="ppt-element ppt-shape" data-id="ABC123defg" data-type="shape" style="position: absolute; left: 50px; top: 200px; width: 100px; height: 80px; background: #FF0000;">
            <div class="shape-text"></div>
          </div>
          <div class="ppt-element ppt-shape" data-id="XyZ987abCd" data-type="shape" style="position: absolute; left: 200px; top: 200px; width: 100px; height: 80px; background: #00FF00;">
            <div class="shape-text"></div>
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化，应该成功
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size
        )

        # 验证结果：包含原始元素和2个新元素
        assert len(result) == 3

        # 验证原始元素
        original_element = next(el for el in result if el.id == "original1")
        assert original_element.type == "text"
        assert original_element.content == "原始文本"

        # 验证新元素
        new_element_1 = next(el for el in result if el.id == "ABC123defg")
        assert new_element_1.type == "shape"

        new_element_2 = next(el for el in result if el.id == "XyZ987abCd")
        assert new_element_2.type == "shape"

    @pytest.mark.asyncio
    async def test_optimize_layout_with_invalid_new_elements_raises_error(self, service):
        """测试包含无效新元素ID的布局优化应该报错"""
        elements = [
            ElementData(
                id="original1",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="原始文本"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        # LLM创建了无效格式的新元素
        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="original1" data-type="text" style="position: absolute; left: 150px; top: 80px; width: 700px; height: 100px;">
            原始文本
          </div>
          <div class="ppt-element ppt-shape" data-id="custom-bg-1" data-type="shape" style="position: absolute; left: 50px; top: 200px; width: 100px; height: 80px;">
            <div class="shape-text"></div>
          </div>
          <div class="ppt-element ppt-shape" data-id="arrow-2" data-type="shape" style="position: absolute; left: 200px; top: 200px; width: 100px; height: 80px;">
            <div class="shape-text"></div>
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化，应该抛出包含无效ID的错误
        with pytest.raises(ValueError, match="布局优化出现无效元素ID") as exc_info:
            await service.optimize_layout(
                slide_id="slide_001",
                elements=elements,
                canvas_size=canvas_size
            )

        # 验证错误消息包含无效的ID
        error_message = str(exc_info.value)
        assert "custom-bg-1" in error_message
        assert "arrow-2" in error_message
        assert "nanoid(10)" in error_message

    @pytest.mark.asyncio
    async def test_validate_element_ids_edge_cases(self, service):
        """测试元素ID验证的边缘情况"""
        # 原始元素
        original = [
            ElementData(
                id="valid123ID",
                type="text",
                left=100,
                top=50,
                width=200,
                height=50,
                content="测试"
            )
        ]

        # 测试各种ID格式
        test_cases = [
            # (optimized_ids, should_pass, description)
            (["valid123ID"], True, "只有原始元素"),
            (["valid123ID", "ABC123defg"], True, "添加有效新元素ID"),
            (["valid123ID", "1234567890"], True, "添加纯数字有效ID"),
            (["valid123ID", "ABCDEFGHIJ"], True, "添加纯大写有效ID"),
            (["valid123ID", "abcdefghij"], True, "添加纯小写有效ID"),
            (["valid123ID", "invalid-id"], False, "无效ID：包含连字符"),
            (["valid123ID", "short"], False, "无效ID：长度不足"),
            (["valid123ID", "way_too_long_for_this_id"], False, "无效ID：长度过长"),
            (["valid123ID", "ABC@123#def"], False, "无效ID：包含特殊字符"),
        ]

        for optimized_ids, should_pass, description in test_cases:
            # 创建优化后的元素列表
            optimized = []
            for element_id in optimized_ids:
                if element_id == "valid123ID":
                    # 原始元素
                    optimized.append(original[0])
                else:
                    # 新元素
                    optimized.append(ElementData(
                        id=element_id,
                        type="shape",
                        left=50,
                        top=50,
                        width=100,
                        height=80
                    ))

            if should_pass:
                # 应该不抛出异常
                try:
                    service._validate_optimized_elements(optimized, original, None)
                except ValueError:
                    pytest.fail(f"验证应该通过: {description}")
            else:
                # 应该抛出异常
                with pytest.raises(ValueError, match="布局优化出现无效元素ID"):
                    service._validate_optimized_elements(optimized, original, None)

    @pytest.mark.asyncio
    async def test_optimize_layout_with_new_parameters(self, service):
        """测试带新参数的布局优化流程"""
        # 模拟元素
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="对比分析：优势与劣势"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        # 模拟LLM响应（应该体现智能分析的影响）
        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="text_001" data-type="text" style="position: absolute; left: 200px; top: 100px; width: 600px; height: 80px; font-size: 36px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px;">
            对比分析：优势与劣势
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化（带新参数）
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size,
            content_analysis="这是一个对比分析类内容，包含优势和劣势的比较，适合使用左右对比布局",
            layout_type_hint="comparison"
        )

        # 验证结果
        assert len(result) == 1
        assert result[0].id == "text_001"
        assert result[0].content == "对比分析：优势与劣势"  # 内容保持不变
        # 验证新参数影响了布局（位置和样式应该比基础优化更智能）
        assert result[0].left == 200.0  # 位置应该体现对比布局的特点

    @pytest.mark.asyncio
    async def test_optimize_layout_with_content_analysis_only(self, service):
        """测试仅包含content_analysis参数的布局优化"""
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="步骤一：准备工作"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="text_001" data-type="text" style="position: absolute; left: 150px; top: 100px; width: 700px; height: 60px; font-size: 28px; border-left: 4px solid #007bff; padding-left: 15px;">
            步骤一：准备工作
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化（仅带content_analysis）
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size,
            content_analysis="这是一个流程说明类内容，按步骤进行说明，适合垂直流程布局"
        )

        # 验证结果
        assert len(result) == 1
        assert result[0].id == "text_001"
        assert result[0].content == "步骤一：准备工作"
        assert result[0].left == 150.0
        assert result[0].top == 100.0

    @pytest.mark.asyncio
    async def test_optimize_layout_with_layout_type_hint_only(self, service):
        """测试仅包含layout_type_hint参数的布局优化"""
        elements = [
            ElementData(
                id="text_001",
                type="text",
                left=100,
                top=50,
                width=600,
                height=80,
                content="核心概念"
            )
        ]

        canvas_size = CanvasSize(width=1000, height=562.5)

        optimized_html = """
        <div class="ppt-canvas" style="width: 1000px; height: 562.5px; position: relative; background: white;">
          <div class="ppt-element ppt-text" data-id="text_001" data-type="text" style="position: absolute; left: 300px; top: 150px; width: 400px; height: 100px; font-size: 32px; text-align: center; background: #f8f9fa; border: 2px solid #dee2e6; border-radius: 50%;">
            核心概念
          </div>
        </div>
        """

        service.ai_client.ai_call.return_value = optimized_html

        # 执行优化（仅带layout_type_hint）
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size,
            layout_type_hint="center_focus"
        )

        # 验证结果
        assert len(result) == 1
        assert result[0].id == "text_001"
        assert result[0].content == "核心概念"
        assert result[0].left == 300.0  # 位置应该体现中心聚焦布局
        assert result[0].top == 150.0

    @pytest.mark.asyncio
    async def test_optimize_layout_validation_failure(self, service):
        """测试布局优化验证失败（回退到原始元素）"""
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

        # 执行优化，应该回退到原始元素
        result = await service.optimize_layout(
            slide_id="slide_001",
            elements=elements,
            canvas_size=canvas_size
        )

        # 验证回退到原始元素
        assert len(result) == 1
        assert result[0].id == "text_001"
        assert result[0].content == "测试标题"
        assert result[0].left == 100.0  # 原始位置
        assert result[0].top == 50.0
        assert result[0].width == 600.0
        assert result[0].height == 80.0