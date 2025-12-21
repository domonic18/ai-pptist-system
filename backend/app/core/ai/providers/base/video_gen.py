"""
文生视频能力Provider基类（未来扩展）
"""

from abc import abstractmethod
from typing import Set

from app.core.ai.base import BaseAIProvider
from app.core.ai.models import ModelCapability, VideoGenerationResult


class BaseVideoGenProvider(BaseAIProvider):
    """文生视频Provider基类"""
    
    def get_capabilities(self) -> Set[ModelCapability]:
        """获取支持的能力"""
        return {ModelCapability.VIDEO_GEN}
    
    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        fps: int = 24,
        **kwargs
    ) -> VideoGenerationResult:
        """
        生成视频接口
        
        Args:
            prompt: 视频描述提示词
            duration: 视频时长（秒）
            fps: 帧率
            **kwargs: 其他参数
            
        Returns:
            VideoGenerationResult: 视频生成结果
        """
        pass

