"""
对话能力Provider基类
"""

from abc import abstractmethod
from typing import List, Dict, Set, Union, AsyncGenerator

from app.core.ai.base import BaseAIProvider
from app.core.ai.models import ModelCapability


class BaseChatProvider(BaseAIProvider):
    """对话Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        """获取支持的能力"""
        return {ModelCapability.CHAT}
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        对话接口
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制输出的随机性
            max_tokens: 最大生成token数
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            对话结果（文本）或流式生成器
        """
        pass

