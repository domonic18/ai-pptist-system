"""
硅基流动(SiliconFlow) 图片生成提供商
基于 SiliconFlow API 实现
支持多种文生图模型：Qwen/Qwen-Image、Kwai-Kolors/Kolors 等
"""

from typing import Optional, Dict, Any
import aiohttp
import json

from app.core.ai.providers.base.image_gen import BaseImageGenProvider
from app.core.ai.models import ImageGenerationResult
from app.core.ai.tracker import MLflowTracingMixin
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class SiliconFlowImageProvider(BaseImageGenProvider, MLflowTracingMixin):
    """硅基流动 图片生成提供商"""

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "Qwen/Qwen-Image-Edit-2509",
        "Qwen/Qwen-Image-Edit",
        "Qwen/Qwen-Image",
        "Kwai-Kolors/Kolors"
    ]

    # Qwen模型支持的尺寸
    QWEN_IMAGE_SIZES = [
        "1328x1328",  # 1:1
        "1664x928",   # 16:9
        "928x1664",   # 9:16
        "1472x1140",  # 4:3
        "1140x1472",  # 3:4
        "1584x1056",  # 3:2
        "1056x1584",  # 2:3
    ]

    # Kolors模型支持的尺寸
    KOLORS_IMAGE_SIZES = [
        "1024x1024",  # 1:1
        "960x1280",   # 3:4
        "768x1024",   # 3:4
        "720x1440",   # 1:2
        "720x1280",   # 9:16
    ]

    # 错误映射
    ERROR_CODES = {
        400: "请求参数错误",
        401: "API密钥无效",
        429: "API调用频率限制",
        500: "服务器内部错误",
        502: "网关错误",
        503: "服务不可用",
    }

    def __init__(self, model_config):
        """
        初始化硅基流动提供商

        Args:
            model_config: AI模型配置对象
        """
        # 初始化基类
        BaseImageGenProvider.__init__(self, model_config)
        MLflowTracingMixin.__init__(self)

        # API配置
        self.api_key = model_config.api_key
        self.base_url = getattr(model_config, 'base_url', 'https://api.siliconflow.cn/v1')

        # 模型名称
        self.model = getattr(model_config, 'model_name', 'Qwen/Qwen-Image')

        # 验证模型是否支持
        if self.model not in self.SUPPORTED_MODELS:
            logger.warning(
                f"模型 {self.model} 可能不受支持，支持的模型: {self.SUPPORTED_MODELS}",
                operation="siliconflow_model_warning"
            )

        logger.info(
            "SiliconFlowImageProvider初始化成功",
            operation="siliconflow_init_success",
            model=self.model,
            base_url=self.base_url
        )

    def get_provider_name(self) -> str:
        """获取Provider名称"""
        return "siliconflow"

    def _get_image_size_options(self) -> list:
        """
        获取当前模型支持的图片尺寸选项

        Returns:
            list: 支持的尺寸列表
        """
        if self.model.startswith("Kwai-Kolors"):
            return self.KOLORS_IMAGE_SIZES
        else:
            # Qwen模型
            return self.QWEN_IMAGE_SIZES

    def _validate_and_adjust_size(self, size: str) -> str:
        """
        验证并调整图片尺寸

        Args:
            size: 尺寸字符串，如 "1024x1024"

        Returns:
            str: 调整到最接近的有效尺寸
        """
        available_sizes = self._get_image_size_options()

        if size in available_sizes:
            return size

        # 如果尺寸不支持，使用第一个可用尺寸
        logger.warning(
            f"尺寸 {size} 不受 {self.model} 支持，使用默认值 {available_sizes[0]}",
            operation="size_fallback"
        )
        return available_sizes[0]

    def _prepare_request_payload(
        self,
        prompt: str,
        size: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        batch_size: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        准备API请求参数

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸
            negative_prompt: 负面提示词
            batch_size: 批次大小
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 请求参数字典
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "batch_size": batch_size,
        }

        # 根据模型添加特定参数
        if self.model.startswith("Qwen"):
            # Qwen模型参数
            if size:
                # Qwen-Image-Edit模型不支持 image_size 参数
                if "-Image-Edit" not in self.model:
                    adjusted_size = self._validate_and_adjust_size(size)
                    payload["image_size"] = adjusted_size

            if negative_prompt:
                payload["negative_prompt"] = negative_prompt

            # cfg 参数（Classifier-Free Guidance）
            cfg = kwargs.get("guidance_scale")
            if cfg is not None:
                payload["cfg"] = cfg

        elif self.model.startswith("Kwai-Kolors"):
            # Kolors模型参数
            if size:
                adjusted_size = self._validate_and_adjust_size(size)
                payload["image_size"] = adjusted_size

            if negative_prompt:
                payload["negative_prompt"] = negative_prompt

            # guidance_scale
            guidance_scale = kwargs.get("guidance_scale", 7.5)
            payload["guidance_scale"] = guidance_scale

            # num_inference_steps
            num_steps = kwargs.get("num_inference_steps", 20)
            payload["num_inference_steps"] = num_steps

            # seed
            seed = kwargs.get("seed")
            if seed is not None:
                payload["seed"] = seed

            # cfg
            cfg = kwargs.get("cfg")
            if cfg is not None:
                payload["cfg"] = cfg

        # 添加参考图片（如果支持）
        ref_images = kwargs.get("ref_images")
        if ref_images and self.model == "Qwen/Qwen-Image-Edit-2509":
            if len(ref_images) > 0:
                payload["image"] = ref_images[0]
                if len(ref_images) > 1:
                    payload["image2"] = ref_images[1]
                if len(ref_images) > 2:
                    payload["image3"] = ref_images[2]

        logger.debug(
            "准备请求参数",
            operation="siliconflow_prepare_payload",
            model=self.model,
            payload_keys=list(payload.keys()),
            has_size="image_size" in payload,
            has_negative="negative_prompt" in payload
        )

        return payload

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图片

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸（如 "1024x1024"）
            quality: 图片质量（standard 或 hd）
            style: 图片风格（vivid 或 natural）
            **kwargs: 其他参数
                - negative_prompt: 负面提示词
                - batch_size: 生成数量
                - ref_images: 参考图片列表
                - guidance_scale: 引导强度
                - num_inference_steps: 推理步数
                - seed: 随机种子
                - cfg: Classifier-Free Guidance 值

        Returns:
            ImageGenerationResult: 图片生成结果
        """
        try:
            # 记录输入参数
            logger.info(
                "开始调用SiliconFlow API生成图片",
                operation="siliconflow_generate_start",
                model=self.model,
                prompt_length=len(prompt),
                size=size,
                quality=quality,
                style=style
            )

            # 准备请求参数
            payload = self._prepare_request_payload(
                prompt=prompt,
                size=size,
                **kwargs
            )

            # 设置请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # API URL
            url = f"{self.base_url}/images/generations"

            logger.debug(
                "发送API请求",
                operation="siliconflow_api_request",
                url=url,
                payload_size=len(str(payload))
            )

            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:

                    # 获取响应状态码
                    status_code = response.status

                    logger.debug(
                        "收到API响应",
                        operation="siliconflow_api_response",
                        status_code=status_code
                    )

                    # 检查响应状态
                    if status_code != 200:
                        error_text = await response.text()
                        error_message = self.ERROR_CODES.get(
                            status_code,
                            f"API错误: {status_code}"
                        )

                        logger.error(
                            "API请求失败",
                            operation="siliconflow_api_error",
                            status_code=status_code,
                            error_message=error_message,
                            error_response=error_text
                        )

                        return ImageGenerationResult(
                            success=False,
                            error_message=f"{error_message}: {error_text[:200]}"
                        )

                    # 解析响应
                    response_data = await response.json()

                    logger.debug(
                        "API响应解析完成",
                        operation="siliconflow_parse_response",
                        response_keys=list(response_data.keys()),
                        has_images="images" in response_data
                    )

                    # 提取图片URL
                    if "images" in response_data and response_data["images"]:
                        images = response_data["images"]
                        image_url = images[0].get("url")

                        if image_url:
                            logger.info(
                                "图片生成成功",
                                operation="siliconflow_generation_success",
                                image_url_preview=image_url[:100]
                            )

                            # 构建元数据
                            metadata = {
                                "model": self.model,
                                "prompt": prompt,
                                "size": size,
                                "quality": quality,
                                "style": style,
                                "total_images": len(images),
                                "response_data": response_data
                            }

                            # 添加额外参数到元数据
                            for key, value in kwargs.items():
                                if value is not None:
                                    metadata[key] = value

                            return ImageGenerationResult(
                                success=True,
                                image_url=image_url,
                                metadata=metadata
                            )
                        else:
                            logger.error(
                                "API响应中没有图片URL",
                                operation="siliconflow_no_image_url",
                                response_preview=str(response_data)[:200]
                            )
                            return ImageGenerationResult(
                                success=False,
                                error_message="API响应中没有图片URL"
                            )
                    else:
                        logger.error(
                            "API响应格式错误",
                            operation="siliconflow_bad_response",
                            response_preview=str(response_data)[:200]
                        )
                        return ImageGenerationResult(
                            success=False,
                            error_message=f"API响应格式错误: {str(response_data)[:200]}"
                        )

        except aiohttp.ClientError as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(
                error_msg,
                operation="siliconflow_network_error",
                exception=e
            )
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            logger.error(
                error_msg,
                operation="siliconflow_json_error",
                exception=e
            )
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )

        except Exception as e:
            error_msg = f"图片生成失败: {str(e)}"
            logger.error(
                error_msg,
                operation="siliconflow_generation_failed",
                exception=e
            )
            return ImageGenerationResult(
                success=False,
                error_message=error_msg
            )
