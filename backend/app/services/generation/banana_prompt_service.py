"""
Banana图片生成提示词服务
基于YAML模板生成文生图的提示词
"""

from typing import List
from app.prompts.utils import load_prompt_template


class BananaPromptService:
    """Banana图片生成提示词服务"""

    def __init__(self):
        """初始化提示词服务"""
        self.template = load_prompt_template('presentation/banana_image_generation')

    def generate_slide_prompt(
        self,
        title: str,
        points: List[str],
        ppt_title: str,
        page_index: int,
        total_pages: int
    ) -> str:
        """
        生成单页幻灯片的图片生成提示词

        Args:
            title: 页面标题
            points: 页面要点列表
            ppt_title: PPT整体标题
            page_index: 当前页面序号（从1开始）
            total_pages: PPT总页数

        Returns:
            str: 格式化后的提示词
        """
        # 格式化要点列表
        points_str = "\n".join([f"- {point}" for point in points])

        # 使用模板生成提示词
        prompt = self.template.format(
            title=title,
            points=points_str,
            ppt_title=ppt_title,
            page_index=page_index,
            total_pages=total_pages
        )

        return prompt
