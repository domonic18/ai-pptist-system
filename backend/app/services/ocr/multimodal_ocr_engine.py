"""
多模态OCR引擎服务
使用支持视觉能力的AI模型（如qwen-vl）进行图片文字识别
"""

import json
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger
from app.core.storage import get_storage_service, download_image_by_key
from app.services.ai_model.management_service import ManagementService
from app.core.config.config import settings
from app.core.ai.factory import AIProviderFactory
from app.core.ai.models import ModelCapability

logger = get_logger(__name__)

# OCR提示词文件路径
OCR_PROMPT_PATH = "ocr/multimodal_text_recognition"


def _load_ocr_prompt() -> str:
    """
    从YAML文件加载OCR识别提示词

    Returns:
        str: 完整的OCR提示词（系统提示词 + 用户提示词）
    """
    try:
        from app.prompts.utils import load_prompt_template_config

        # 加载提示词配置
        config = load_prompt_template_config(OCR_PROMPT_PATH)

        # 合并系统提示词和用户提示词
        system_prompt = config.get('system_prompt', '')
        user_prompt = config.get('user_prompt', '')

        # 组合完整的提示词
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        logger.info("成功加载OCR提示词模板", extra={"path": OCR_PROMPT_PATH})

        return full_prompt

    except Exception as e:
        logger.warning(
            "加载OCR提示词文件失败，使用默认提示词",
            extra={"error": str(e)}
        )
        # 返回简化的默认提示词
        return """请分析这张图片中的所有文字内容，并以JSON格式返回识别结果。

对于每个文字区域，请提取以下信息：
1. text: 文字的完整内容
2. bbox: 文字边界框坐标 {x, y, width, height}
3. font: 字体信息 (size, family, weight, color, align)

返回格式：{"texts": [{"text": "...", "bbox": {...}, "font": {...}}]}"""


class MultimodalOCREngine:
    """
    多模态OCR引擎

    使用支持视觉能力的AI模型（如qwen-vl）进行图片文字识别
    """

    def __init__(self, db: AsyncSession, model_name: Optional[str] = None):
        """
        初始化多模态OCR引擎

        Args:
            db: 数据库会话
            model_name: 指定使用的模型名称（如不传则使用默认模型）
        """
        self.db = db
        self.model_name = model_name
        self._provider = None
        self._model_config = None
        # 最近一次解析的图片尺寸（用于下游坐标换算）
        self.last_image_width: Optional[int] = None
        self.last_image_height: Optional[int] = None

        logger.info(
            "多模态OCR引擎初始化",
            extra={"model_name": model_name or "default"}
        )

    async def _get_provider(self):
        """
        获取Vision Provider实例（懒加载单例）

        Returns:
            Vision Provider实例
        """
        if self._provider is not None:
            return self._provider

        try:
            # 获取AI模型管理服务
            model_service = ManagementService(self.db)

            # 获取模型配置
            if self.model_name:
                # 使用指定模型
                model_config = await model_service.get_model_for_edit(self.model_name)
                if not model_config:
                    raise ValueError(f"模型不存在: {self.model_name}")
            else:
                # 使用默认vision模型（内部方法，包含api_key）
                model_config = await model_service.get_default_model_for_use(capability="vision")

            if not model_config:
                raise ValueError("未找到可用的视觉模型，请先配置支持vision能力的模型")

            self._model_config = model_config

            # 从provider_mapping获取vision的provider名称
            provider_mapping = model_config.get("provider_mapping", {})
            provider_name = provider_mapping.get("vision")

            if not provider_name:
                # 尝试使用chat能力（很多模型vision和chat共用）
                provider_name = provider_mapping.get("chat")

            if not provider_name:
                raise ValueError(
                    f"模型 {model_config['name']} 未配置vision或chat provider"
                )

            # 创建provider实例
            from app.core.ai.config import ModelConfig as AIModelConfig

            ai_model_config = AIModelConfig.from_dict(model_config)

            # 使用vision能力，如果模型不支持则使用chat
            try:
                provider = AIProviderFactory.create_provider(
                    capability=ModelCapability.VISION,
                    provider_name=provider_name,
                    model_config=ai_model_config
                )
            except ValueError:
                # 如果不支持vision，尝试使用chat（很多模型通过chat接口处理多模态）
                provider = AIProviderFactory.create_provider(
                    capability=ModelCapability.CHAT,
                    provider_name=provider_name,
                    model_config=ai_model_config
                )

            self._provider = provider

            logger.info(
                "多模态OCR Provider创建成功",
                extra={
                    "provider": provider_name,
                    "model": model_config["ai_model_name"]
                }
            )

            return self._provider

        except Exception as e:
            logger.error(
                "创建多模态OCR Provider失败",
                extra={"error": str(e)}
            )
            raise

    async def parse_from_cos_key(
        self,
        cos_key: str
    ) -> List[Dict]:
        """
        从COS Key解析图片

        通过统一存储服务从COS拉取图片，然后进行OCR识别

        Args:
            cos_key: 图片COS Key（如：ai-generated/ppt/xxx/slide_0.png）

        Returns:
            List[Dict]: 识别结果列表
            [
                {
                    "text": "识别的文字",
                    "bbox": {"x": int, "y": int, "width": int, "height": int},
                    "confidence": float,
                    "font": {
                        "size": int,
                        "family": str,
                        "weight": str,
                        "color": str,
                        "align": str
                    }
                },
                ...
            ]
        """
        try:
            logger.info("开始多模态OCR识别", extra={"cos_key": cos_key})

            # 1. 下载图片并获取预签名URL（使用统一下载方法）
            storage = get_storage_service()
            presigned_url = await storage.generate_url(cos_key, expires=3600, operation="get")

            logger.info(
                "预签名URL生成成功",
                extra={
                    "cos_key": cos_key,
                    "url_prefix": presigned_url[:100]
                }
            )

            # 2. 下载图片并获取实际尺寸（使用统一下载方法）
            image_data, image_format = await download_image_by_key(cos_key, storage)

            # 获取图片尺寸（用于OCR坐标系统 & 前端坐标映射）
            import io
            from PIL import Image

            image = Image.open(io.BytesIO(image_data))
            image_width, image_height = image.size
            self.last_image_width = int(image_width)
            self.last_image_height = int(image_height)

            logger.info(
                "图片尺寸检测完成",
                extra={
                    "cos_key": cos_key,
                    "width": image_width,
                    "height": image_height
                }
            )

            # 3. 调用多模态模型API（传递图片URL和实际尺寸，约束坐标范围）
            result = await self._call_multimodal_api(presigned_url, int(image_width), int(image_height))

            logger.info(
                "多模态OCR识别完成",
                extra={"cos_key": cos_key, "text_count": len(result)}
            )

            return result

        except Exception as e:
            logger.error(
                "多模态OCR识别失败",
                extra={"cos_key": cos_key, "error": str(e)}
            )
            raise

    async def _call_multimodal_api(self, image_url: str, image_width: int, image_height: int) -> List[Dict]:
        """
        调用多模态模型API

        Args:
            image_url: 图片URL（可以是data URL或预签名URL）
            image_width: 图片实际宽度（像素）
            image_height: 图片实际高度（像素）

        Returns:
            List[Dict]: 识别结果列表
        """
        # 获取provider
        provider = await self._get_provider()

        # 加载OCR提示词
        base_prompt = _load_ocr_prompt()
        
        # 在提示词中明确图片尺寸
        ocr_prompt = f"""{base_prompt}

**重要提示：图片实际尺寸**
- 图片宽度：{image_width} 像素
- 图片高度：{image_height} 像素
- 所有坐标必须在此范围内：x ∈ [0, {image_width}], y ∈ [0, {image_height}]
- 请确保所有bbox坐标都基于此实际尺寸，不要假定其他分辨率（如1920x1080）
"""

        # 构建请求消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ocr_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

        logger.info(
            "调用多模态模型API",
            extra={
                "model": self._model_config["ai_model_name"] if self._model_config else "unknown",
                "image_size": f"{image_width}x{image_height}",
                "timeout": settings.MULTIMODAL_OCR_TIMEOUT
            }
        )

        # 调用API（使用配置的超时时间）
        response = await provider.vision_chat(
            messages=messages,
            temperature=0.1,  # 使用低温度以获得更稳定的结果
            max_tokens=4096,
            timeout=settings.MULTIMODAL_OCR_TIMEOUT  # 超时时间（秒）
        )

        # 如果返回的是dict（包含content字段），提取内容
        if isinstance(response, dict):
            content = response.get("content", "")
        else:
            content = response

        logger.info(
            "多模态模型响应成功",
            extra={
                "response_length": len(content),
                "response_preview": content[:200],
                "image_size": f"{image_width}x{image_height}"
            }
        )

        # 解析JSON响应
        return self._parse_model_response(content)

    def _parse_model_response(self, response: str) -> List[Dict]:
        """
        解析模型响应

        Args:
            response: 模型返回的JSON字符串

        Returns:
            List[Dict]: 格式化后的识别结果
        """
        # 尝试提取JSON（模型可能会在JSON前后添加说明文字）
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError(
                f"模型响应中未找到有效的JSON格式。响应内容: {response[:500]}"
            )

        json_str = response[json_start:json_end]

        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"解析模型响应JSON失败: {e}。JSON内容: {json_str[:500]}"
            )

        # 检查返回格式
        if "texts" not in result:
            raise ValueError(
                f"模型响应缺少texts字段。响应内容: {json_str[:500]}"
            )

        texts = result["texts"]

        if not isinstance(texts, list):
            raise ValueError("texts字段应为数组")

        # 格式化结果
        formatted = []
        for item in texts:
            try:
                # 验证必需字段
                if "text" not in item:
                    continue
                if "bbox" not in item:
                    continue

                bbox = item["bbox"]
                if not all(k in bbox for k in ["x", "y", "width", "height"]):
                    continue

                # 获取字体信息，提供默认值
                font_info = item.get("font", {})
                font = {
                    "size": int(font_info.get("size", 16)),
                    "family": font_info.get("family", "Microsoft YaHei"),
                    "weight": font_info.get("weight", "normal"),
                    "color": font_info.get("color", "#000000"),
                    "align": font_info.get("align", "left")
                }

                # 验证颜色格式
                if not font["color"].startswith("#"):
                    # 如果颜色不是十六进制，尝试转换或使用默认值
                    font["color"] = "#000000"

                formatted.append({
                    "text": item["text"],
                    "bbox": {
                        "x": int(bbox["x"]),
                        "y": int(bbox["y"]),
                        "width": int(bbox["width"]),
                        "height": int(bbox["height"])
                    },
                    "confidence": 0.95,  # 多模态模型通常不提供置信度，使用默认值
                    "font": font
                })

            except (ValueError, TypeError) as e:
                logger.warning(
                    "跳过无效的文字区域",
                    extra={"item": item, "error": str(e)}
                )
                continue

        if not formatted:
            logger.warning("多模态OCR未检测到有效文字")

        return formatted
