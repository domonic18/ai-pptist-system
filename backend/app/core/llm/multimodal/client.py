"""
多模态分析客户端
基于现有LLM架构的多模态模型调用封装
"""

from typing import Dict, Any, Optional, List
from app.core.log_utils import get_logger
from app.core.llm.client import AIClient
from app.core.llm.setting import ModelSetting
from app.core.llm.tracker import MLflowTracker

logger = get_logger(__name__)


class MultimodalClient:
    """多模态分析客户端"""

    def __init__(self):
        """初始化多模态客户端"""
        self.ai_client = AIClient()
        self.mlflow_tracker = MLflowTracker()

    async def analyze_image(
        self,
        image_data: str,
        prompt: str,
        model_config: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        分析图片内容

        Args:
            image_data: 图片数据（base64编码）
            prompt: 分析提示词
            model_config: 模型配置
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            分析结果字典
        """
        try:
            # 构建多模态消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]

            # 使用现有的AI客户端执行调用
            response = await self._execute_multimodal_call(
                messages=messages,
                model_config=model_config,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return self._parse_multimodal_response(response)

        except Exception as e:
            logger.error(
                "多模态分析失败",
                operation="multimodal_analysis_failed",
                exception=e,
                model_config=model_config
            )
            raise

    async def _execute_multimodal_call(
        self,
        messages: List[Dict[str, Any]],
        model_config: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> str:
        """
        执行多模态调用

        Args:
            messages: 消息列表
            model_config: 模型配置
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            AI响应内容
        """
        # 解析模型配置，确保使用支持视觉的模型
        if model_config:
            # 如果指定了模型配置，使用它
            model_setting = await self._resolve_model_config(model_config)
        else:
            # 否则使用默认的视觉模型
            model_setting = await self._get_default_vision_model()

        if not model_setting:
            raise ValueError("没有找到可用的视觉模型")

        # 构建系统提示词
        system_prompt = "你是一个专业的图像分析助手，请根据用户提供的图片和提示词进行分析。"

        # 将消息列表转换为用户提示词
        user_prompt = self._format_messages_for_text(messages)

        # 记录多模态调用开始
        logger.info(
            "开始多模态调用",
            operation="multimodal_call_start",
            model_name=model_setting.name,
            provider=model_setting.provider,
            mlflow_enabled=self.mlflow_tracker.is_initialized
        )

        # 使用MLflow追踪执行多模态调用
        try:
            # 为多模态调用添加特定标签
            multimodal_tags = {
                "call_type": "multimodal",
                "model_type": "vision",
                "has_image": "true",
                "provider": model_setting.provider
            }

            # 使用MLflow追踪执行调用
            response = await self.mlflow_tracker.execute_with_tracking(
                model_setting,
                lambda: self.ai_client.ai_call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    ai_model_config={
                        "model_id": model_setting.id,
                        "model_name": model_setting.ai_model_name
                    }
                ),
                tags=multimodal_tags
            )

            logger.info(
                "多模态调用完成",
                operation="multimodal_call_completed",
                model_name=model_setting.name,
                response_length=len(response)
            )

            return response

        except Exception as e:
            logger.error(
                "多模态调用失败",
                operation="multimodal_call_failed",
                exception=e,
                model_name=model_setting.name
            )
            raise

    async def _resolve_model_config(self, model_config: Dict[str, Any]) -> Optional[ModelSetting]:
        """解析模型配置"""
        if model_config.get("model_id"):
            model_id = model_config["model_id"]

            # 确保模型管理器已加载
            await self.ai_client.model_manager.ensure_loaded()

            # 查找支持视觉的模型
            vision_models = [
                model for model in self.ai_client.model_manager.text_models + self.ai_client.model_manager.image_models
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

    async def _get_default_vision_model(self) -> Optional[ModelSetting]:
        """获取默认的视觉模型"""
        await self.ai_client.model_manager.ensure_loaded()

        vision_models = [
            model for model in self.ai_client.model_manager.text_models + self.ai_client.model_manager.image_models
            if getattr(model, 'supports_vision', False) and model.enabled
        ]

        if not vision_models:
            logger.warning("没有找到可用的视觉模型")
            return None

        # 优先使用默认模型，否则使用第一个可用的视觉模型
        default_model = next(
            (model for model in vision_models if model.is_default),
            vision_models[0]
        )

        logger.info(f"使用默认视觉模型: {default_model.name}")
        return default_model

    def _format_messages_for_text(self, messages: List[Dict[str, Any]]) -> str:
        """将多模态消息格式化为文本格式"""
        formatted_messages = []
        for message in messages:
            if message["role"] == "user":
                content_parts = []
                for content in message["content"]:
                    if content["type"] == "text":
                        content_parts.append(content["text"])
                    elif content["type"] == "image_url":
                        content_parts.append("[图片内容]")
                formatted_messages.append("用户: " + " ".join(content_parts))
        return "\n".join(formatted_messages)

    def _parse_multimodal_response(self, response: str) -> Dict[str, Any]:
        """解析多模态响应"""
        import json
        import re

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