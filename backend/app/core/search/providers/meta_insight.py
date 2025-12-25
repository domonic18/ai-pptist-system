"""
腾讯云MetaInsight搜索提供商
提供高级语义搜索和图像理解能力
"""

import time
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.core.storage import COSStorage
from app.core.config import settings
from app.core.log_utils import get_logger

from .base import BaseSearchProvider, SearchResult
from .meta_insight_client import MetaInsightAPIClient

logger = get_logger(__name__)


class MetaInsightProvider(BaseSearchProvider):
    """腾讯云MetaInsight搜索提供商"""

    def __init__(self, db: AsyncSession, cos_service: Optional[COSStorage] = None):
        super().__init__(db)
        self.repository = ImageRepository(db)
        self.cos_service = cos_service or COSStorage()

        # MetaInsight配置
        self.region = settings.cos_region
        self.bucket = settings.cos_bucket
        self.enabled = self._check_meta_insight_availability()

        # 搜索配置
        self.default_match_threshold = settings.meta_insight_default_threshold
        self.max_results = settings.meta_insight_max_results

        # 初始化API客户端
        self.api_client = MetaInsightAPIClient() if self.enabled else None

    def _check_meta_insight_availability(self) -> bool:
        """检查MetaInsight服务是否可用"""
        try:
            # 检查必要的配置项
            if not settings.cos_secret_id:
                logger.warning("MetaInsight配置缺失: cos_secret_id")
                return False

            if not settings.cos_secret_key:
                logger.warning("MetaInsight配置缺失: cos_secret_key")
                return False

            if not settings.cos_region:
                logger.warning("MetaInsight配置缺失: cos_region")
                return False

            if not settings.cos_bucket:
                logger.warning("MetaInsight配置缺失: cos_bucket")
                return False

            if not settings.meta_insight_dataset_name:
                logger.warning("MetaInsight配置缺失: meta_insight_dataset_name")
                return False

            logger.info("MetaInsight服务配置检查通过")
            return True

        except Exception as e:
            logger.error(f"MetaInsight服务配置检查失败: {e}")
            return False

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        match_threshold: Optional[int] = None,
        search_type: str = "semantic",
        **kwargs
    ) -> List[SearchResult]:
        """
        基于MetaInsight的语义搜索

        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 返回结果数量
            match_threshold: 匹配精度阈值（百分比）
            search_type: 搜索类型
            **kwargs: 其他参数

        Returns:
            MetaInsight搜索结果
        """
        start_time = time.time()

        try:
            if not self.enabled:
                logger.warning("MetaInsight服务不可用，返回空结果")
                return []

            self._validate_search_params(query, user_id, limit)

            if match_threshold is None:
                match_threshold = self.default_match_threshold

            logger.info(
                "开始MetaInsight搜索",
                extra={
                    "query": query[:100],
                    "user_id": user_id,
                    "search_type": search_type,
                    "match_threshold": match_threshold
                }
            )

            # 调用MetaInsight API进行图像搜索（基于文本描述）
            api_results = await self.api_client.search_by_text(
                text=query,
                limit=limit,
                match_threshold=match_threshold,
                preprocess_strategy="smart_truncate"
            )

            # 转换API结果为内部格式

            results = await self._convert_api_results_to_search_results(api_results, search_type)

            duration_ms = (time.time() - start_time) * 1000

            await self._log_search_activity(
                "MetaInsight", query, user_id, len(results), duration_ms
            )

            return results

        except Exception as e:
            logger.error(
                "MetaInsight搜索失败",
                extra={
                    "query": query[:100],
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            return []

    async def search_similar(
        self,
        reference_image_id: str,
        user_id: str,
        limit: int = 5,
        match_threshold: Optional[int] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        基于MetaInsight的以图搜图

        Args:
            reference_image_id: 参考图片ID
            user_id: 用户ID
            limit: 返回结果数量
            match_threshold: 匹配精度阈值（百分比）
            **kwargs: 其他参数

        Returns:
            相似图片搜索结果
        """
        start_time = time.time()

        try:
            if not self.enabled:
                logger.warning("MetaInsight服务不可用，返回空结果")
                return []

            self._validate_search_params(user_id=user_id, limit=limit)

            if match_threshold is None:
                match_threshold = self.default_match_threshold

            # 获取参考图片信息
            reference_image = await self.repository.get_image_by_id(reference_image_id)
            if not reference_image:
                return []

            # 检查用户权限
            if reference_image.user_id != user_id:
                return []

            if not reference_image.cos_key:
                logger.warning(
                    "参考图片未存储在COS中，无法进行MetaInsight搜索",
                    extra={"reference_image_id": reference_image_id}
                )
                return []

            # 构建COS URI
            cos_uri = self.api_client._build_cos_uri(reference_image.cos_key)

            # 调用MetaInsight API进行以图搜图
            api_results = await self.api_client.search_by_image(
                image_uri=cos_uri,
                limit=limit,
                match_threshold=match_threshold
            )

            # 转换API结果为内部格式
            results = await self._convert_api_results_to_search_results(api_results, "visual")

            duration_ms = (time.time() - start_time) * 1000

            await self._log_search_activity(
                "MetaInsight相似", None, user_id, len(results), duration_ms
            )

            return results

        except Exception as e:
            logger.error(
                "MetaInsight相似搜索失败",
                extra={
                    "reference_image_id": reference_image_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            return []

    async def _convert_api_results_to_search_results(
        self,
        api_results: List[Dict[str, Any]],
        search_type: str
    ) -> List[SearchResult]:
        """
        将MetaInsight API结果转换为内部SearchResult格式

        Args:
            api_results: MetaInsight API返回的结果
            search_type: 搜索类型

        Returns:
            转换后的SearchResult列表
        """
        search_results = []

        for api_result in api_results:
            try:
                # 从COS URI中提取COS key
                cos_uri = api_result.get("URI", "")
                cos_key = self._extract_cos_key_from_uri(cos_uri)

                if not cos_key:
                    logger.warning(f"无法从URI中提取COS key: {cos_uri}")
                    continue

                # 根据COS key查找对应的图片记录
                image = await self.repository.get_image_by_cos_key(cos_key)
                if not image:
                    logger.warning(f"未找到COS key对应的图片记录: {cos_key}")
                    continue

                # 获取分数并转换为0-1范围的置信度
                score = api_result.get("Score", 0)
                confidence = score / 100.0 if score > 0 else 0.0

                # 创建SearchResult对象
                search_result = SearchResult(
                    image_id=image.id,
                    score=score,
                    match_type=f"meta_insight_{search_type}",
                    confidence=confidence,
                    metadata={
                        "cos_uri": cos_uri,
                        "cos_key": cos_key,
                        "search_type": search_type,
                        "api_score": score,
                        "real_api": True
                    }
                )

                search_results.append(search_result)

            except Exception as e:
                logger.error(
                    f"转换API结果失败: {e}",
                    extra={
                        "api_result": api_result,
                        "search_type": search_type
                    }
                )
                continue

        # 按分数排序
        search_results.sort(key=lambda x: x.score, reverse=True)

        return search_results

    def _extract_cos_key_from_uri(self, cos_uri: str) -> Optional[str]:
        """
        从COS URI中提取COS key

        Args:
            cos_uri: COS URI，格式如 cos://bucket-appid/path/to/file

        Returns:
            提取的COS key
        """
        try:
            if not cos_uri.startswith("cos://"):
                return None

            # 移除 cos:// 前缀
            path = cos_uri[6:]

            # 分割bucket和key部分
            if "/" not in path:
                return None

            # 第一个/后面的就是key
            first_slash_index = path.index("/")
            cos_key = path[first_slash_index + 1:]

            return cos_key if cos_key else None

        except Exception as e:
            logger.error(f"提取COS key失败: {e}", extra={"cos_uri": cos_uri})
            return None