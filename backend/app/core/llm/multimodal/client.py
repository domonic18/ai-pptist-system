"""
多模态分析客户端
基于现有LLM架构的多模态模型调用封装
"""

from typing import Dict, Any, Optional
import json
import re
from app.core.log_utils import get_logger
from app.core.llm.setting import ModelSetting
from app.core.llm.tracker import MLflowTracker
from app.core.llm.models import ModelManager

logger = get_logger(__name__)


class MultimodalClient:
    """多模态分析客户端"""

    def __init__(self):
        """初始化多模态客户端"""
        self.model_manager = ModelManager()
        self.mlflow_tracker = MLflowTracker()

    async def analyze_image(
        self,
        image_data: str,
        prompt: str,
        model_config: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析图片内容

        Args:
            image_data: 图片数据（base64编码）
            prompt: 分析提示词
            model_config: 模型配置
            max_tokens: 最大token数
            temperature: 温度参数
            system_prompt: 系统提示词（可选，如果不提供则使用默认提示词）

        Returns:
            分析结果字典
        """
        try:
            # 解析模型配置
            model_setting = await self._resolve_model_config(model_config)
            if not model_setting:
                raise ValueError("没有找到可用的视觉模型")

            # 使用默认系统提示词如果没有提供
            if system_prompt is None:
                system_prompt = "你是一个专业的图像分析助手，请根据用户提供的图片和提示词进行分析。"

            # 直接执行多模态调用
            client = model_setting.get_client()

            # 构建多模态消息
            multimodal_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._process_image_data(image_data)
                            }
                        }
                    ]
                }
            ]

            # 记录多模态调用开始
            logger.info(
                "开始多模态调用",
                operation="multimodal_call_start",
                model_name=model_setting.name,
                provider=model_setting.provider,
                mlflow_enabled=self.mlflow_tracker.is_initialized
            )

            # 为多模态调用添加特定标签
            multimodal_tags = {
                "call_type": "multimodal",
                "model_type": "vision",
                "has_image": "true",
                "provider": model_setting.provider
            }

            response = await self.mlflow_tracker.execute_with_tracking(
                model_setting,
                lambda: client.chat.completions.create(
                    model=model_setting.ai_model_name,
                    messages=multimodal_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                tags=multimodal_tags
            )

            content = response.choices[0].message.content

            logger.info(
                "多模态调用完成",
                operation="multimodal_call_completed",
                model_name=model_setting.name,
                response_length=len(content)
            )

            return self._parse_multimodal_response(content)

        except Exception as e:
            logger.error(
                "多模态分析失败",
                operation="multimodal_analysis_failed",
                exception=e,
                model_config=model_config
            )
            raise

    async def _resolve_model_config(self, model_config: Dict[str, Any]) -> Optional[ModelSetting]:
        """解析模型配置"""
        if model_config.get("model_id"):
            model_id = model_config["model_id"]

            # 确保模型管理器已加载
            await self.model_manager.ensure_loaded()

            # 查找支持视觉的模型
            vision_models = [
                model for model in self.model_manager.text_models + self.model_manager.image_models
                if getattr(model, 'supports_vision', False) and model.enabled
            ]

            if not vision_models:
                logger.warning(f"没有找到可用的视觉模型，请求模型ID: {model_id}")
                return None

            # 查找指定模型
            found_model = next((model for model in vision_models if model.id == model_id), None)

            if not found_model:
                logger.warning(f"未找到指定的视觉模型: {model_id}")
                return None

            logger.info(f"使用视觉模型: {found_model.name} (ID: {found_model.id})")
            return found_model
        return None

    def _process_image_data(self, image_data: str) -> str:
        """
        处理图片数据，确保格式正确

        Args:
            image_data: 图片数据，可能是纯base64或完整的data URL

        Returns:
            格式正确的图片URL
        """
        # 如果已经是完整的data URL，直接返回
        if image_data.startswith('data:image/'):
            return image_data

        # 如果是纯base64数据，添加PNG格式前缀（前端生成的是PNG格式）
        if image_data and len(image_data) > 100:  # 简单的base64数据检查
            return f"data:image/png;base64,{image_data}"

        # 如果数据无效，记录警告
        logger.warning(
            "图片数据格式异常",
            operation="image_data_format_warning",
            data_length=len(image_data) if image_data else 0
        )
        return image_data

    def _parse_multimodal_response(self, response: str) -> Dict[str, Any]:
        """解析多模态响应"""
        try:
            # 尝试直接解析为JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果不是JSON格式，尝试从文本中提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        # 如果无法解析为JSON，返回原始文本
        return {"analysis": response}
