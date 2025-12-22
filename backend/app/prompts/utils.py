"""
Prompt工具模块
提供Prompt相关的工具函数和辅助类
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import yaml
from jinja2 import Template

from app.core.config import settings
from app.core.log_utils import get_logger

logger = get_logger(__name__)


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


def load_prompt_template(template_path: str) -> Template:
    """
    加载提示词模板

    Args:
        template_path: 模板路径（相对于app/prompts/目录）

    Returns:
        jinja2.Template: 加载的模板对象

    Example:
        template = load_prompt_template('presentation/banana_image_generation')
        prompt = template.format(
            title="AI发展史",
            points="- AI诞生\n- 深度学习",
            ppt_title="技术演进",
            page_index=2,
            total_pages=10
        )
    """
    try:
        # 构建完整路径
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / "prompts" / f"{template_path}.yml"

        if not file_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {file_path}")

        # 读取YAML文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 提取模板内容
        template_content = data.get('template', '')

        # 创建Jinja2模板
        template = Template(template_content)

        logger.info(f"成功加载提示词模板: {template_path}")

        return template

    except Exception as e:
        logger.error(f"加载提示词模板失败: {template_path}, 错误: {e}")
        # 返回一个空模板，避免程序崩溃
        return Template("")


def load_prompt_template_config(template_path: str) -> Dict[str, Any]:
    """
    加载提示词模板配置

    Args:
        template_path: 模板路径（相对于app/prompts/目录）

    Returns:
        Dict: 模板配置信息（参数、示例等）
    """
    try:
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / "prompts" / f"{template_path}.yml"

        if not file_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return data

    except Exception as e:
        logger.error(f"加载提示词模板配置失败: {template_path}, 错误: {e}")
        return {}