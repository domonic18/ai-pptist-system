"""
Prompt工具模块
提供Prompt相关的工具函数和辅助类
"""

from typing import Dict, Any, Optional, Tuple
from app.core.config import settings


class PromptHelper:
    """Prompt辅助工具类"""

    def __init__(self, prompt_manager):
        self.prompt_manager = prompt_manager

    def prepare_prompts(
        self,
        category: str,
        template_name: str,
        user_prompt_params: Dict[str, Any],
        system_prompt_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, float, int]:
        """
        准备提示词和配置

        Args:
            category: 提示词类别
            template_name: 模板名称
            user_prompt_params: 用户提示词参数
            system_prompt_params: 系统提示词参数

        Returns:
            tuple: (system_prompt, user_prompt, temperature, max_tokens)
        """
        system_prompt_params = system_prompt_params or {}

        # 渲染系统提示词
        system_prompt = self.prompt_manager.render_system_prompt(
            category, template_name, **system_prompt_params
        )

        # 渲染用户提示词
        user_prompt = self.prompt_manager.render_user_prompt(
            category, template_name, **user_prompt_params
        )

        # 获取模板配置
        template_config = self.prompt_manager.get_template_config(category, template_name)
        temperature = template_config.get('temperature', settings.ai_default_temperature)
        max_tokens = template_config.get('max_tokens', settings.ai_default_max_tokens)

        return system_prompt, user_prompt, temperature, max_tokens