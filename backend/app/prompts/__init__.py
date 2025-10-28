"""
Prompt模板管理器
负责加载、渲染和管理所有AI交互的提示词模板
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from app.core.config import settings
from app.core.log_utils import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class PromptManager:
    """Prompt模板管理器"""

    def __init__(self):
        """初始化prompt管理器"""
        self.prompts_dir = Path(__file__).parent
        self.env = Environment(loader=FileSystemLoader(str(self.prompts_dir)))
        self._templates_cache: Dict[str, Dict[str, Any]] = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """加载所有模板文件"""
        try:
            for category_dir in self.prompts_dir.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith('__'):
                    category_name = category_dir.name
                    self._templates_cache[category_name] = {}

                    for template_file in category_dir.glob('*.yml'):
                        template_name = template_file.stem
                        try:
                            with open(template_file, 'r', encoding='utf-8') as f:
                                template_data = yaml.safe_load(f)
                                self._templates_cache[category_name][template_name] = template_data
                        except Exception as e:
                            logger.error(
                                message=f"加载模板文件失败: {template_file}",
                                operation="load_template_error",
                                exception=e
                            )

            logger.info(
                "Prompt模板加载完成",
                extra_data={"categories": list(self._templates_cache.keys())},
                operation="prompt_templates_loaded"
            )

        except Exception as e:
            logger.error(
                "加载Prompt模板失败",
                operation="load_templates_error",
                exception=e
            )

    def get_template(self, category: str, template_name: str) -> Optional[Dict[str, Any]]:
        """获取指定模板"""
        try:
            return self._templates_cache.get(category, {}).get(template_name)
        except Exception as e:
            logger.error(
                message=f"获取模板失败: {category}/{template_name}",
                operation="get_template_error",
                exception=e
            )
            return None

    def render_system_prompt(self, category: str, template_name: str, **kwargs) -> str:
        """渲染系统提示词"""
        template_data = self.get_template(category, template_name)
        if not template_data:
            raise ValueError(f"模板不存在: {category}/{template_name}")

        system_prompt = template_data.get('system_prompt', '')
        if not system_prompt:
            raise ValueError(f"模板中未找到system_prompt: {category}/{template_name}")

        return self._render_template(system_prompt, **kwargs)

    def render_user_prompt(self, category: str, template_name: str, **kwargs) -> str:
        """渲染用户提示词"""
        template_data = self.get_template(category, template_name)
        if not template_data:
            raise ValueError(f"模板不存在: {category}/{template_name}")

        user_prompt = template_data.get('user_prompt', '')
        if not user_prompt:
            raise ValueError(f"模板中未找到user_prompt: {category}/{template_name}")

        return self._render_template(user_prompt, **kwargs)

    def get_template_config(self, category: str, template_name: str) -> Dict[str, Any]:
        """获取模板配置信息"""
        template_data = self.get_template(category, template_name)
        if not template_data:
            return {}

        return {
            'temperature': template_data.get('temperature', settings.ai_default_temperature),
            'max_tokens': template_data.get('max_tokens', settings.ai_default_max_tokens),
            'description': template_data.get('description', ''),
            'version': template_data.get('version', '1.0')
        }

    def _render_template(self, template_str: str, **kwargs) -> str:
        """渲染模板字符串"""
        try:
            template = Template(template_str)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(
                message="模板渲染失败",
                operation="render_template_error",
                exception=e,
                extra_data={"template": template_str[:100], "kwargs": kwargs}
            )
            raise

    def list_templates(self) -> Dict[str, list]:
        """列出所有可用的模板"""
        result = {}
        for category, templates in self._templates_cache.items():
            result[category] = list(templates.keys())
        return result

    def reload_templates(self):
        """重新加载所有模板"""
        self._templates_cache.clear()
        self._load_all_templates()


# 全局prompt管理器实例
prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """获取prompt管理器实例"""
    return prompt_manager


from .utils import PromptHelper