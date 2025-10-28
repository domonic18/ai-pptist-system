"""
AI模型设置类
"""

import openai
from typing import Dict, Any
from app.core.config import settings


class ModelSetting:
    """AI模型设置类"""

    def __init__(self, config_dict: Dict[str, Any]):
        self.name = config_dict.get("name", "")
        self.api_key = config_dict.get("api_key", "")
        self.base_url = config_dict.get("base_url", "https://api.openai.com/v1")
        self.enabled = config_dict.get("enabled", True)
        self.provider = config_dict.get("provider", "openai")
        self.description = config_dict.get("description", "")

        # 文本生成参数
        self.temperature = config_dict.get("temperature", settings.ai_default_temperature)
        self.max_tokens = config_dict.get("max_tokens", settings.ai_default_max_tokens)

        # 图像生成参数
        self.quality = config_dict.get("quality", "standard")
        self.size = config_dict.get("size", "1024x1024")

        # 网络配置
        self.timeout = config_dict.get("timeout", settings.ai_default_timeout)
        self.max_retries = config_dict.get("max_retries", 1)  # 默认重试2次

        # 默认模型标记
        self.is_default = config_dict.get("is_default", False)

    def get_client(self) -> openai.AsyncOpenAI:
        """获取异步OpenAI客户端"""
        if not self.api_key:
            raise ValueError(f"API key is required for model '{self.name}' but not provided")

        return openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries
        )