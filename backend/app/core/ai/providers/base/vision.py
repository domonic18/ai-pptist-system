"""
多模态能力Provider基类
"""

from abc import abstractmethod
from typing import List, Dict, Any, Set

from app.core.ai.base import BaseAIProvider
from app.core.ai.models import ModelCapability


class BaseVisionProvider(BaseAIProvider):
    """多模态Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        """获取支持的能力"""
        return {ModelCapability.VISION}
    
    @abstractmethod
    async def vision_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        多模态对话接口
        
        Args:
            messages: 对话消息列表，可以包含图片
                     格式: [{"role": "user", "content": [
                         {"type": "text", "text": "..."},
                         {"type": "image_url", "image_url": {"url": "..."}}
                     ]}]
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            对话结果（文本）
        """
        pass

