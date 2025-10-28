"""
搜索提供商基类
定义搜索服务的统一接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_utils import get_logger

logger = get_logger(__name__)


class SearchResult:
    """搜索结果封装类"""

    def __init__(
        self,
        image_id: str,
        score: float,
        match_type: str,
        confidence: float,
        metadata: Optional[dict] = None
    ):
        self.image_id = image_id
        self.score = score
        self.match_type = match_type
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "image_id": self.image_id,
            "score": self.score,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class BaseSearchProvider(ABC):
    """搜索提供商基类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger

    @abstractmethod
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        文本搜索

        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 返回结果数量
            **kwargs: 其他搜索参数

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def search_similar(
        self,
        reference_image_id: str,
        user_id: str,
        limit: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """
        以图搜图

        Args:
            reference_image_id: 参考图片ID
            user_id: 用户ID
            limit: 返回结果数量
            **kwargs: 其他搜索参数

        Returns:
            相似图片搜索结果
        """
        pass

    def _validate_search_params(
        self,
        query: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> bool:
        """验证搜索参数"""
        if user_id is None:
            raise ValueError("用户ID不能为空")

        if limit <= 0 or limit > 100:
            raise ValueError("搜索结果数量必须在1-100之间")

        if query is not None and len(query.strip()) == 0:
            raise ValueError("搜索查询不能为空")

        return True

    async def _log_search_activity(
        self,
        search_type: str,
        query: Optional[str],
        user_id: str,
        result_count: int,
        duration_ms: float
    ):
        """记录搜索活动"""
        self.logger.info(
            f"{search_type}搜索完成",
            extra={
                "search_type": search_type,
                "query": query[:100] if query else None,
                "user_id": user_id,
                "result_count": result_count,
                "duration_ms": duration_ms
            }
        )