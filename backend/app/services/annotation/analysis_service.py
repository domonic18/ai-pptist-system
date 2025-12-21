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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.core.redis import redis_client
from app.services.annotation.cache_service import CacheService
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability
from app.repositories.ai_model import AIModelRepository
from app.prompts import get_prompt_manager, PromptHelper

logger = get_logger(__name__)


class AnalysisService:
    """幻灯片分析服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_model_repo = AIModelRepository(db)
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

        最佳实践说明：
        - 图片通过多模态接口的 image_url 参数单独传递
        - 提示词中只包含文本描述，不包含图片的 base64 数据
        - 这样可以避免图片数据重复，减少 token 消耗

        Args:
            slide: 幻灯片数据（包含 screenshot, elements 等字段）
            model_config: 模型配置

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 获取模型配置
        ai_model = None
        if model_config and model_config.get("model_id"):
            ai_model = await self.ai_model_repo.get_model_by_id(model_config["model_id"])
        
        if not ai_model:
            # 获取默认的视觉模型
            vision_models = await self.ai_model_repo.get_models_by_capability('vision')
            if vision_models:
                # 优先使用默认模型，否则使用第一个可用的视觉模型
                ai_model = next(
                    (model for model in vision_models if model.is_default and model.is_enabled),
                    next((model for model in vision_models if model.is_enabled), None)
                )
            
            if not ai_model:
                raise ValueError("没有找到可用的视觉模型")

        # 准备不包含截图的幻灯片数据用于提示词
        screenshot_data = slide.get("screenshot")
        slide_data_for_prompt = {k: v for k, v in slide.items() if k != "screenshot"}

        # 使用提示词模板系统生成分析提示词
        system_prompt, user_prompt, temperature, max_tokens = self.prompt_helper.prepare_prompts(
            category="annotation",
            template_name="slide_analysis",
            user_prompt_params={"slide_data": slide_data_for_prompt}
        )

        # 使用新的统一AI架构
        provider_name = ai_model.get_provider_for_capability('vision') or 'openai_compatible'
        
        model_config_obj = type('ModelConfig', (), {
            'name': ai_model.ai_model_name,
            'base_url': ai_model.base_url,
            'api_key': ai_model.api_key,
            'parameters': ai_model.parameters or {}
        })()
        
        vision_provider = AIProviderFactory.create_provider(
            capability=ModelCapability.VISION,
            provider_name=provider_name,
            model_config=model_config_obj
        )
        
        # 构建消息列表（包含图片）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用vision接口
        response = await vision_provider.chat(
            messages=messages,
            images=[screenshot_data] if screenshot_data else [],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        result = {
            "content": response.get("content", ""),
            "model": response.get("model", ""),
            "usage": response.get("usage", {})
        }

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
