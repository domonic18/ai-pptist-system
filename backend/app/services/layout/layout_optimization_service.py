"""
布局优化Service（核心业务逻辑）
负责LLM调用、结果验证
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.layout_optimization import (
    ElementData,
    CanvasSize,
    OptimizationOptions
)
from app.core.llm.client import AIClient
from app.core.log_utils import get_logger
from app.prompts import get_prompt_manager
from app.prompts.utils import PromptHelper
from app.core.html import HTMLConverter, HTMLParser

logger = get_logger(__name__)


class LayoutOptimizationService:
    """布局优化服务（核心业务逻辑）"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_client = AIClient()
        self.prompt_manager = get_prompt_manager()
        self.prompt_helper = PromptHelper(self.prompt_manager)
        self.html_converter = HTMLConverter()
        self.html_parser = HTMLParser()

    async def optimize_layout(
        self,
        slide_id: str,
        elements: List[ElementData],
        canvas_size: CanvasSize,
        options: Optional[OptimizationOptions] = None,
        user_prompt: Optional[str] = None,
        ai_model_config: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        content_analysis: Optional[str] = None,
        layout_type_hint: Optional[str] = None
    ) -> List[ElementData]:
        """
        优化幻灯片布局的核心方法

        Args:
            slide_id: 幻灯片ID
            elements: 元素列表
            canvas_size: 画布尺寸
            options: 优化选项
            user_prompt: 用户自定义提示词
            ai_model_config: AI模型配置
            temperature: 温度参数，控制生成多样性，None时使用模板默认值
            content_analysis: 内容智能分析结果，用于指导布局选择和优化策略
            layout_type_hint: 布局类型智能提示，基于内容语义分析的推荐布局类型

        Returns:
            List[ElementData]: 优化后的元素列表

        Raises:
            ValueError: 验证失败
            Exception: 其他异常
        """
        # 记录优化开始时的完整信息
        logger.info(
            "==== 布局优化开始 ====",
            operation="optimize_layout_start",
            slide_id=slide_id,
            elements_count=len(elements),
            element_ids=[el.id for el in elements],
            element_types=[el.type for el in elements]
        )

        # 详细记录每个原始元素的信息
        for idx, element in enumerate(elements):
            logger.debug(
                f"原始元素 {idx + 1}/{len(elements)} 详情",
                operation="original_element_detail",
                element_id=element.id,
                element_type=element.type,
                element_left=element.left,
                element_top=element.top,
                element_width=element.width,
                element_height=element.height
            )

        try:
            # 1. 转换PPTist元素为HTML
            html_content = self.html_converter.convert_to_html(
                elements, canvas_size
            )
            logger.info(
                "PPTist元素已转换为HTML",
                operation="convert_to_html",
                html_length=len(html_content)
            )

            # 2. 构建提示词参数
            requirements = self._build_requirements(options, user_prompt)
            user_prompt_params = {
                "canvas_width": canvas_size.width,
                "canvas_height": canvas_size.height,
                "html_content": html_content,
                "requirements": requirements,
                "content_analysis": content_analysis,
                "layout_type_hint": layout_type_hint
            }

            # 3. 准备提示词
            system_prompt, user_prompt, template_temperature, max_tokens = \
                self.prompt_helper.prepare_prompts(
                    category="presentation",
                    template_name="layout_optimization",
                    user_prompt_params=user_prompt_params
                )

            # 使用传入的temperature参数，如果为None则使用模板默认值
            final_temperature = temperature if temperature is not None else template_temperature

            # 记录使用的temperature值
            logger.info(
                "确定temperature参数",
                operation="determine_temperature",
                user_provided_temperature=temperature,
                template_temperature=template_temperature,
                final_temperature=final_temperature
            )

            # 4. 调用LLM（使用现有AIClient）
            logger.info(
                "调用LLM进行HTML布局优化",
                operation="optimize_layout_llm_call",
                slide_id=slide_id
            )

            llm_response = await self.ai_client.ai_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=final_temperature,
                max_tokens=max_tokens,
                ai_model_config=ai_model_config
            )

            logger.info(
                "LLM HTML响应接收完成",
                operation="optimize_layout_llm_response",
                response_length=len(llm_response)
            )

            # 5. 解析HTML响应，提取纯HTML内容
            optimized_html = self.html_parser.extract_html_from_response(llm_response)

            # 6. 解析HTML DOM，转换为PPTist元素
            optimized_elements = self.html_parser.parse_html_to_elements(
                optimized_html, elements
            )

            logger.info(
                "解析LLM返回的HTML元素完成",
                operation="parse_llm_elements_complete",
                llm_elements_count=len(optimized_elements),
                llm_element_ids=[el.id for el in optimized_elements],
                llm_element_types=[el.type for el in optimized_elements]
            )

            # 6.5. 清洗元素数据，移除null/undefined值
            cleaned_elements = self._sanitize_elements_data(optimized_elements)

            logger.info(
                "清洗元素数据完成",
                operation="sanitize_elements_complete",
                cleaned_elements_count=len(cleaned_elements),
                cleaned_element_ids=[el.id for el in cleaned_elements],
                removed_null_fields="(see previous debug logs)"
            )

            # 7. 验证结果（确保内容不变、ID一致等）
            self._validate_optimized_elements(cleaned_elements, elements, user_prompt)

            # 生成优化总结报告
            original_ids = {el.id for el in elements}
            optimized_ids = {el.id for el in cleaned_elements}
            missing = original_ids - optimized_ids
            extra = optimized_ids - original_ids

            logger.info(
                "==== 布局优化完成总结报告 ====",
                operation="optimize_layout_complete_summary",
                slide_id=slide_id,
                summary={
                    "原始元素数量": len(elements),
                    "优化后元素数量": len(cleaned_elements),
                    "变化情况": {
                        "保留元素数量": len(optimized_ids) - len(extra),
                        "新增元素数量": len(extra),
                        "删除元素数量": len(missing)
                    },
                    "删除元素ID列表": sorted(list(missing)) if missing else [],
                    "新增元素ID列表": sorted(list(extra)) if extra else [],
                    "保留元素ID列表": sorted(list(original_ids & optimized_ids))
                },
                detailed_breakdown={
                    "原始元素": {
                        "total": len(elements),
                        "ids": sorted([el.id for el in elements]),
                        "types": {}
                    },
                    "优化后元素": {
                        "total": len(cleaned_elements),
                        "ids": sorted([el.id for el in cleaned_elements]),
                        "types": {}
                    },
                    "操作": {
                        "删除": f"{len(missing)} 个元素",
                        "新增": f"{len(extra)} 个新装饰元素",
                        "保留": f"{len(optimized_ids) - len(extra)} 个原始元素"
                    }
                }
            )

            logger.info(
                "布局优化执行成功",
                operation="optimize_layout_success",
                slide_id=slide_id,
                optimized_count=len(cleaned_elements)
            )

            return cleaned_elements

        except Exception as e:
            import traceback

            # 生成错误发生时的总结报告
            logger.error(
                "==== 布局优化失败总结报告 ====",
                operation="optimize_layout_failed_summary",
                slide_id=slide_id,
                failure_summary={
                    "失败阶段": "捕获到异常前的最后操作阶段",
                    "错误类型": type(e).__name__,
                    "错误消息": str(e),
                    "堆栈追踪": traceback.format_exc(),
                    "原始元素统计": {
                        "总数": len(elements) if 'elements' in locals() else 0,
                        "类型分布": self._count_element_types(elements) if 'elements' in locals() else {}
                    },
                    "处理进度": {
                        "HTML转换完成": 'html_content' in locals(),
                        "提示词准备完成": 'user_prompt_params' in locals(),
                        "LLM调用开始": 'llm_response' in locals(),
                        "HTML解析完成": 'optimized_elements' in locals(),
                        "数据清洗完成": 'cleaned_elements' in locals()
                    }
                }
            )

            logger.error(
                "布局优化执行失败",
                operation="optimize_layout_failed",
                slide_id=slide_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise


    def _build_requirements(self, options: Optional[OptimizationOptions], user_prompt: Optional[str]) -> str:
        """构建优化要求文本"""
        requirements = []

        # 添加用户自定义提示词（如果有）
        if user_prompt and user_prompt.strip():
            requirements.append(f"- 用户特定要求：{user_prompt.strip()}")

        if options:
            if options.keep_colors:
                requirements.append("- 保持原有颜色方案，不得更改元素颜色")
            if options.keep_fonts:
                requirements.append("- 保持原有字体，不得更改font-family")

            style_hints = {
                'professional': '专业、商务、简洁',
                'creative': '创意、活泼、大胆',
                'minimal': '极简、留白、克制'
            }
            style = options.style or 'professional'
            requirements.append(f"- 优化风格：{style_hints.get(style, '专业')}")

        return "\n".join(requirements) if requirements else "全面优化"


    def _validate_optimized_elements(
        self,
        optimized: List[ElementData],
        original: List[ElementData],
        user_prompt: Optional[str] = None
    ):
        """验证优化结果（确保关键内容不变，允许布局变化）"""
        original_ids = {el.id for el in original}
        optimized_ids = {el.id for el in optimized}

        logger.info(
            "验证元素ID一致性",
            operation="validate_element_ids",
            original_ids=sorted(list(original_ids)),
            optimized_ids=sorted(list(optimized_ids))
        )

        # 检查是否有元素缺失
        missing = original_ids - optimized_ids
        extra = optimized_ids - original_ids

        if missing:
            # 允许LLM删除元素，但记录详细警告信息
            removed_elements_detail = []
            for element_id in missing:
                original_element = next((el for el in original if el.id == element_id), None)
                if original_element:
                    removed_elements_detail.append({
                        "id": element_id,
                        "type": original_element.type,
                        "has_content": bool(getattr(original_element, 'content', '')),
                        "content_preview": getattr(original_element, 'content', '')[:100] if getattr(original_element, 'content', '') else "",
                        "left": getattr(original_element, 'left', 0),
                        "top": getattr(original_element, 'top', 0),
                        "width": getattr(original_element, 'width', 0),
                        "height": getattr(original_element, 'height', 0)
                    })

            logger.warning(
                "布局优化中删除了部分元素",
                operation="layout_optimization_removed_elements",
                removed_count=len(missing),
                removed_elements_detail=removed_elements_detail,
                reason="这些元素在LLM返回的HTML中未找到，可能是LLM主动删除或元素转换失败"
            )

            # 检查删除的元素是否包含重要内容
            removed_text_elements = [
                el for el in original
                if el.id in missing and el.type == 'text' and el.content
            ]

            if removed_text_elements:
                logger.warning(
                    "布局优化中删除了文本元素",
                    operation="layout_optimization_removed_text",
                    removed_text_elements=[
                        {
                            "id": el.id,
                            "type": el.type,
                            "content_length": len(el.content) if el.content else 0,
                            "content_preview": el.content[:100] if el.content else ""
                        }
                        for el in removed_text_elements
                    ]
                )

        if extra:
            # 检查新元素的ID是否符合规范（使用nanoid格式）
            from app.core.html.id_generator import PPTIDGenerator
            id_generator = PPTIDGenerator()

            invalid_new_ids = []
            valid_new_ids = []

            for element_id in extra:
                # 严格验证：ID必须符合nanoid(10)格式
                is_valid = id_generator.is_valid_id(element_id)

                if is_valid:
                    valid_new_ids.append(element_id)
                    logger.info(
                        "发现新元素ID",
                        operation="new_element_id",
                        element_id=element_id
                    )
                else:
                    invalid_new_ids.append(element_id)
                    # 提供详细的验证失败信息
                    validation_details = {
                        "element_id": element_id,
                        "length": len(element_id) if element_id else 0,
                        "expected_length": id_generator.ELEMENT_ID_LENGTH,
                        "is_none_or_empty": element_id is None or (element_id and len(element_id) == 0),
                        "has_invalid_chars": False
                    }

                    if element_id:
                        invalid_chars = [char for char in element_id if char not in id_generator.ALPHABET]
                        if invalid_chars:
                            validation_details["has_invalid_chars"] = True
                            validation_details["invalid_chars"] = invalid_chars
                            validation_details["invalid_char_codes"] = [ord(char) for char in invalid_chars]

                    logger.warning(
                        "发现无效的新元素ID",
                        operation="invalid_new_element_id",
                        **validation_details
                    )

            # 只有存在无效ID时才报错
            if invalid_new_ids:
                logger.error(
                    "布局优化中出现了无效ID的新元素",
                    operation="layout_optimization_invalid_element_ids",
                    invalid_elements=sorted(list(invalid_new_ids)),
                    valid_elements=sorted(list(valid_new_ids)),
                    invalid_id_details=[
                        {
                            "id": element_id,
                            "length": len(element_id) if element_id else 0,
                            "chars_valid": all(char in id_generator.ALPHABET for char in element_id) if element_id else False
                        }
                        for element_id in invalid_new_ids
                    ]
                )
                raise ValueError(
                    f"布局优化出现无效元素ID：{invalid_new_ids}。"
                    f"新元素ID必须符合nanoid(10)格式（10位字母数字组合）。"
                )

            if valid_new_ids:
                logger.info(
                    "布局优化成功创建了新的装饰元素",
                    operation="layout_optimization_new_elements_created",
                    new_elements_count=len(valid_new_ids),
                    new_element_ids=sorted(list(valid_new_ids))
                )

                # 详细记录每个新元素的信息
                for element in optimized:
                    if element.id in valid_new_ids:
                        logger.info(
                            f"新元素详情 - ID: {element.id}, 类型: {element.type}, "
                            f"位置: ({element.left}, {element.top}), 尺寸: {element.width}x{element.height}, "
                            f"填充: {element.fill}",
                            operation="new_element_details",
                            element_id=element.id,
                            element_type=element.type,
                            element_left=element.left,
                            element_top=element.top,
                            element_width=element.width,
                            element_height=element.height,
                            element_fill=element.fill
                        )

        # 验证文本内容（如果用户要求保持文本不变）
        self._validate_text_content(optimized, original, user_prompt)

    def _validate_text_content(
        self,
        optimized: List[ElementData],
        original: List[ElementData],
        user_prompt: Optional[str]
    ):
        """
        智能验证文本内容

        根据用户提示词决定是否允许修改文本内容：
        - 如果提示词包含"文字内容不要修改"，则严格保持文本不变
        - 如果用户明确允许修改，则允许文本优化
        - 默认情况下保持文本内容不变
        """
        # 检查用户提示词中是否明确要求保持文本内容不变
        keep_text_unchanged = False
        if user_prompt:
            keep_text_unchanged = any(keyword in user_prompt.lower()
                                    for keyword in [
                                        '文字内容不要修改',
                                        '不要修改文字',
                                        '保持文字不变',
                                        '文本内容不变',
                                        '不要改动文字'
                                    ])

        # 如果用户明确要求保持文本不变，则强制恢复原始内容
        # TODO: 暂时注释掉强制恢复逻辑，允许AI优化文本内容
        # if keep_text_unchanged:
        #     logger.info(
        #         "用户要求保持文本内容不变，强制恢复原始文本",
        #         operation="validate_text_content",
        #         user_prompt=user_prompt
        #     )
        #     for orig_el in original:
        #         if orig_el.type == "text" and orig_el.content:
        #             opt_el = next((el for el in optimized if el.id == orig_el.id), None)
        #             if opt_el and opt_el.content != orig_el.content:
        #                 logger.warning(
        #                     "文本内容被修改，已恢复原始内容",
        #                     element_id=orig_el.id,
        #                     original_content=orig_el.content[:50],
        #                     optimized_content=opt_el.content[:50]
        #                 )
        #                 # 强制恢复原始内容
        #                 opt_el.content = orig_el.content
        # else:
        #     # 用户没有明确要求保持文本不变，允许文本优化
        #     logger.info(
        #         "用户允许文本内容优化，不强制恢复原始文本",
        #         operation="validate_text_content",
        #         user_prompt=user_prompt
        #     )
        #     # 记录文本变化（但不强制恢复）
        #     for orig_el in original:
        #         if orig_el.type == "text" and orig_el.content:
        #             opt_el = next((el for el in optimized if el.id == orig_el.id), None)
        #             if opt_el and opt_el.content != orig_el.content:
        #                 logger.info(
        #                     "文本内容被优化",
        #                     element_id=orig_el.id,
        #                     original_content=orig_el.content[:50],
        #                     optimized_content=opt_el.content[:50]
        #                 )

        # 现在始终允许文本优化，不强制恢复原始内容
        logger.info(
            "文本内容优化已启用，允许AI优化文本表达",
            operation="validate_text_content",
            user_prompt=user_prompt
        )
        # 记录文本变化
        for orig_el in original:
            if orig_el.type == "text" and orig_el.content:
                opt_el = next((el for el in optimized if el.id == orig_el.id), None)
                if opt_el and opt_el.content != orig_el.content:
                    logger.info(
                        "文本内容被优化",
                        element_id=orig_el.id,
                        original_content=orig_el.content[:50],
                        optimized_content=opt_el.content[:50]
                    )

    def _count_element_types(self, elements: List[ElementData]) -> dict:
        """统计元素类型分布"""
        type_counts = {}
        for element in elements:
            type_name = element.type or 'unknown'
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        return type_counts

    def _sanitize_elements_data(self, elements: List[ElementData]) -> List[ElementData]:
        """
        清洗元素数据，移除null值，避免前端运行时错误

        Args:
            elements: 原始元素列表

        Returns:
            List[ElementData]: 清洗后的元素列表
        """
        logger.info(
            "开始清洗元素数据",
            operation="sanitize_elements_data_start",
            elements_count=len(elements)
        )

        cleaned_elements = []
        null_fields_removed = 0

        for element in elements:
            # 获取元素的所有字段，使用exclude_none=True排除null值
            element_dict = element.model_dump(exclude_none=True)

            # 清洗单个元素的数据
            cleaned_dict = self._sanitize_single_element(element_dict)

            # 计算移除的null字段数量
            removed_count = len([k for k, v in element_dict.items() if v is None])
            null_fields_removed += removed_count

            # 创建新的ElementData对象，使用exclude_none=True确保不包含null值
            cleaned_element = ElementData(**cleaned_dict)
            cleaned_elements.append(cleaned_element)

            if removed_count > 0:
                logger.debug(
                    "元素数据清洗完成",
                    operation="sanitize_single_element",
                    element_id=element.id,
                    element_type=element.type,
                    removed_fields_count=removed_count
                )

        logger.info(
            "元素数据清洗完成",
            operation="sanitize_elements_data_complete",
            original_elements_count=len(elements),
            cleaned_elements_count=len(cleaned_elements),
            total_null_fields_removed=null_fields_removed
        )

        return cleaned_elements

    def _sanitize_single_element(self, element_dict: dict) -> dict:
        """
        清洗单个元素数据，移除null值

        Args:
            element_dict: 元素的字典表示

        Returns:
            dict: 清洗后的字典
        """
        cleaned = {}

        # 需要保留的特殊字段（即使为空字符串也要保留）
        preserve_empty_fields = {
            'id', 'type', 'content', 'defaultFontName', 'defaultColor'
        }

        for key, value in element_dict.items():
            # 跳过null值
            if value is None:
                continue

            # 对于特定字段，如果为空字符串则保留（避免前端访问undefined）
            if key in preserve_empty_fields and value == "":
                cleaned[key] = value
                continue

            # 对于嵌套对象（如text, outline），递归清洗
            if isinstance(value, dict):
                cleaned_nested = self._sanitize_single_element(value)
                # 只有在清洗后的对象不为空时才保留
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
                continue

            # 对于数组类型（如viewBox），检查是否包含null值
            if isinstance(value, list):
                # 过滤掉数组中的null值
                filtered_list = [item for item in value if item is not None]
                if filtered_list:  # 只有在数组不为空时才保留
                    cleaned[key] = filtered_list
                continue

            # 对于其他类型，直接保留
            cleaned[key] = value

        return cleaned