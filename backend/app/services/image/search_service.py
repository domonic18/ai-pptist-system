"""
图片搜索服务
处理图片搜索相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageSearchService:
    """图片搜索服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ImageRepository(db)

    async def search_images(
        self,
        query: str,
        user_id: str,
        limit: int = 20,
        match_threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """搜索图片 - 使用MetaInsight搜索"""
        try:
            # 使用MetaInsight进行搜索
            from app.core.search.providers import MetaInsightProvider
            meta_insight_provider = MetaInsightProvider(self.db)

            meta_insight_results = await meta_insight_provider.search(
                query, user_id, limit, match_threshold
            )

            # 获取图片详情
            search_results = []
            for result in meta_insight_results:
                image = await self.repository.get_image_by_id(result.image_id)
                if image:
                    search_results.append({
                        "id": image.id,
                        "prompt": image.description or image.original_filename,
                        "model_name": image.generation_model or "unknown",
                        "width": image.width,
                        "height": image.height,
                        "file_size": image.file_size,
                        "mime_type": image.mime_type,
                        "created_at": image.created_at,
                        "cos_key": image.cos_key,
                        "url": image.image_url,
                        "match_type": result.match_type,
                        "confidence": result.confidence,
                        "score": result.score,
                        "metadata": result.metadata
                    })

            return {
                "success": True,
                "results": search_results,
                "total": len(search_results),
                "query": query,
                "search_type": "meta_insight"
            }

        except Exception as e:
            logger.error(f"MetaInsight搜索失败: {e}")
            return {
                "success": False,
                "results": [],
                "total": 0,
                "error": str(e)
            }

    async def get_user_tags(self, user_id: str) -> List[str]:
        """获取用户的所有图片标签"""
        try:
            # 获取用户的所有图片
            images, _ = await self.repository.get_user_images(user_id, 0, 1000)

            # 提取所有标签并去重
            all_tags = set()
            for image in images:
                if image.tags:
                    all_tags.update(image.tags)

            return sorted(list(all_tags))

        except Exception as e:
            logger.error(f"获取用户标签失败: {e}")
            return []

    async def search_by_tags(
        self,
        tags: List[str],
        user_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """根据标签搜索图片"""
        try:
            # 获取用户的所有图片
            images, _ = await self.repository.get_user_images(user_id, 0, 1000)

            # 根据标签过滤图片
            filtered_images = []
            for image in images:
                if image.tags and any(tag in image.tags for tag in tags):
                    filtered_images.append(image)

            # 限制结果数量
            filtered_images = filtered_images[:limit]

            # 准备返回结果
            results = []
            for image in filtered_images:
                matching_tags = [tag for tag in tags if tag in image.tags]
                results.append({
                    "id": image.id,
                    "prompt": image.description or image.original_filename,
                    "model_name": image.generation_model or "unknown",
                    "width": image.width,
                    "height": image.height,
                    "file_size": image.file_size,
                    "mime_type": image.mime_type,
                    "created_at": image.created_at,
                    "cos_key": image.cos_key,
                    "url": image.image_url,
                    "match_type": "tag",
                    "confidence": len(matching_tags) / len(tags) if tags else 0.0
                })

            return {
                "success": True,
                "results": results,
                "total": len(results),
                "tags": tags
            }

        except Exception as e:
            logger.error(f"按标签搜索失败: {e}")
            return {
                "success": False,
                "results": [],
                "total": 0,
                "error": str(e)
            }

    def _calculate_relevance_score(self, image, query: str) -> float:
        """计算搜索相关性分数"""
        score = 0.0
        query_lower = query.lower()

        # 检查文件名匹配
        if image.original_filename and query_lower in image.original_filename.lower():
            score += 0.3

        # 检查描述匹配
        if image.description and query_lower in image.description.lower():
            score += 0.4

        # 检查标签匹配
        if image.tags:
            for tag in image.tags:
                if query_lower in tag.lower():
                    score += 0.3
                    break

        return min(score, 1.0)