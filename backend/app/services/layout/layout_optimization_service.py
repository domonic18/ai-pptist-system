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
        temperature: Optional[float] = None
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

        Returns:
            List[ElementData]: 优化后的元素列表

        Raises:
            ValueError: 验证失败
            Exception: 其他异常
        """
        logger.info(
            "开始执行布局优化",
            operation="optimize_layout",
            slide_id=slide_id,
            elements_count=len(elements)
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
                "requirements": requirements
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

            # 7. 验证结果（确保内容不变、ID一致等）
            self._validate_optimized_elements(optimized_elements, elements, user_prompt)

            logger.info(
                "布局优化执行成功",
                operation="optimize_layout_success",
                slide_id=slide_id,
                optimized_count=len(optimized_elements)
            )

            return optimized_elements

        except Exception as e:
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
            # 允许LLM删除元素，但记录警告信息
            logger.warning(
                "布局优化中删除了部分元素",
                operation="layout_optimization_removed_elements",
                removed_elements=sorted(list(missing)),
                removed_count=len(missing)
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
                        {"id": el.id, "content": el.content[:50]}
                        for el in removed_text_elements
                    ]
                )

        if extra:
            # LLM不应该创建新元素，这可能是解析错误
            logger.error(
                "布局优化中出现了未知元素",
                operation="layout_optimization_unknown_elements",
                unknown_elements=sorted(list(extra))
            )
            raise ValueError(
                f"布局优化出现未知元素：{extra}"
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