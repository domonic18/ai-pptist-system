"""
幻灯片分析服务

职责:
- 处理单个幻灯片的AI分析
- 多模态分析和结果处理
- 缓存交互
"""

import json
import re
from typing import Dict, Any, Optional

from app.core.log_utils import get_logger
from app.core.redis import redis_client
from app.services.annotation.cache_service import CacheService
from app.core.llm.multimodal.client import MultimodalClient
from app.core.llm.models import ModelManager
from app.prompts import get_prompt_manager, PromptHelper

logger = get_logger(__name__)


class AnalysisService:
    """幻灯片分析服务"""

    def __init__(self):
        self.model_manager = ModelManager()
        self.multimodal_client = MultimodalClient()
        self.prompt_manager = get_prompt_manager()
        self.prompt_helper = PromptHelper(self.prompt_manager)
        self.cache_service = CacheService(redis_client)

    async def analyze_slide(
        self,
        slide: Dict[str, Any],
        model_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析单个幻灯片

        Args:
            slide: 幻灯片数据
            model_config: 模型配置

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 1. 检查缓存
        cache_key = self.cache_service.generate_cache_key(slide)
        cached_result = await self.cache_service.get_cached_result(cache_key)
        if cached_result:
            logger.info(f"使用缓存结果: slide_id={slide.get('slide_id')}")
            return cached_result

        # 2. 调用多模态分析服务
        try:
            result = await self._call_multimodal_analysis(slide, model_config)

            # 3. 处理结果
            processed_result = self._process_analysis_result(result, slide)

            # 4. 缓存结果
            await self.cache_service.cache_result(cache_key, processed_result)

            return processed_result

        except Exception as e:
            logger.error(
                f"幻灯片分析失败: slide_id={slide.get('slide_id')}",
                exception=e
            )
            # 返回失败结果
            return {
                "slide_id": slide.get("slide_id", "unknown"),
                "status": "failed",
                "error": str(e)
            }

    async def _call_multimodal_analysis(
        self,
        slide: Dict[str, Any],
        model_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        调用多模态分析

        Args:
            slide: 幻灯片数据
            model_config: 模型配置

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 获取模型ID，如果没有提供则使用默认的视觉模型
        model_id = model_config.get("model_id") if model_config else None

        if not model_id:
            # 获取默认的视觉模型
            await self.model_manager.ensure_loaded()
            vision_models = [
                model for model in self.model_manager.text_models + self.model_manager.image_models
                if getattr(model, 'supports_vision', False) and model.enabled
            ]
            if vision_models:
                # 优先使用默认模型，否则使用第一个可用的视觉模型
                default_vision_model = next(
                    (model for model in vision_models if model.is_default),
                    vision_models[0]
                )
                model_id = default_vision_model.id
            else:
                raise ValueError("没有找到可用的视觉模型")

        # 使用提示词模板系统生成分析提示词
        system_prompt, user_prompt, temperature, max_tokens = self.prompt_helper.prepare_prompts(
            category="annotation",
            template_name="slide_analysis",
            user_prompt_params={"slide_data": slide}
        )

        # 使用多模态客户端分析图片
        result = await self.multimodal_client.analyze_image(
            image_data=slide.get("screenshot", ""),
            prompt=user_prompt,
            model_config={"model_id": model_id},
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )

        return result

    def _process_analysis_result(self, raw_result: Dict[str, Any], slide: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理分析结果，确保格式正确

        Args:
            raw_result: 原始分析结果
            slide: 幻灯片数据

        Returns:
            处理后的分析结果
        """
        slide_id = slide.get("slide_id", "unknown")

        # 如果结果已经是标准格式，直接返回
        if all(key in raw_result for key in ["page_type", "layout_type", "element_annotations"]):
            return {
                "slide_id": slide_id,
                "status": "success",
                **raw_result
            }

        # 如果结果包含analysis字段，尝试解析
        if "analysis" in raw_result:
            analysis_text = raw_result["analysis"]
            try:
                # 尝试从文本中提取JSON
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group())
                    return {
                        "slide_id": slide_id,
                        "status": "success",
                        **parsed_result
                    }
            except:
                pass

        # 如果无法解析，返回失败结果
        return {
            "slide_id": slide_id,
            "status": "failed",
            "error": "无法解析分析结果"
        }
