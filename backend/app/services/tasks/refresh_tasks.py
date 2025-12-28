"""图片URL刷新任务"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from celery import group, chain
from celery.result import AsyncResult

from .celery_app import celery_app
from app.services.cache.url.service import ImageURLService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def refresh_url_cache(self, image_key: str, force_refresh: bool = False) -> dict:  # type: ignore
    """刷新单个图片URL缓存

    Args:
        image_key: 图片键
        force_refresh: 是否强制刷新

    Returns:
        包含刷新结果的字典
    """
    try:
        import asyncio

        # 在Celery中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        url_service = ImageURLService()
        start_time = datetime.utcnow()

        result = loop.run_until_complete(
            url_service.get_image_url(
                image_key=image_key,
                force_refresh=force_refresh,
                use_cache=True
            )
        )

        loop.close()

        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "success": result.success,
            "image_key": image_key,
            "url": result.url,
            "response_time": duration,
            "from_cache": result.from_cache,
            "error": str(result.error) if result.error else None,
        }
    except Exception as e:
        logger.error(f"Failed to refresh URL cache for {image_key}: {e}")
        raise


@celery_app.task(bind=True)
def batch_refresh_url_cache(
    self,
    image_keys: List[str],
    batch_size: int = 50,
    max_workers: int = 10,
) -> dict:
    """批量刷新图片URL缓存

    Args:
        image_keys: 图片键列表
        batch_size: 每批处理数量
        max_workers: 最大并发数

    Returns:
        批量处理结果统计
    """
    try:
        # 分批处理
        total = len(image_keys)
        batch_count = (total + batch_size - 1) // batch_size
        batches = [
            image_keys[i * batch_size:(i + 1) * batch_size]
            for i in range(batch_count)
        ]

        results = {
            "total": len(image_keys),
            "success": 0,
            "failed": 0,
            "batch_count": len(batches),
            "start_time": datetime.utcnow().isoformat(),  # type: ignore
        }

        for batch_idx, batch in enumerate(batches):
            logger.info(
                f"Processing batch {batch_idx + 1}/{len(batches)}, "
                f"size: {len(batch)}"
            )

            # 创建组任务
            job = group(
                refresh_url_cache.s(image_key) for image_key in batch
            )

            # 执行批量任务
            batch_result = job.apply_async()

            # 等待批次完成
            batch_results = batch_result.get(timeout=300)

            # 统计结果
            for res in batch_results:
                if res.get("success"):
                    results["success"] += 1
                else:
                    results["failed"] += 1

        results["end_time"] = datetime.utcnow().isoformat()
        results["duration"] = 0.0  # type: ignore

        logger.info(
            f"Batch refresh completed: {results['success']} success, "
            f"{results['failed']} failed, "
            f"duration: {results['duration']:.2f}s"
        )

        return results

    except Exception as e:
        logger.error(f"Batch refresh failed: {e}")
        raise


@celery_app.task()
def schedule_periodic_refresh(image_key: str, refresh_interval: int = 3600) -> str:  # type: ignore
    """安排定期刷新任务

    Args:
        image_key: 图片键
        refresh_interval: 刷新间隔（秒）

    Returns:
        任务ID
    """
    # 使用apply_async设置ETA
    task = refresh_url_cache.apply_async(
        args=[image_key],
        eta=datetime.utcnow() + timedelta(seconds=refresh_interval),
    )

    logger.info(
        f"Scheduled periodic refresh for {image_key}, "
        f"interval: {refresh_interval}s, task_id: {task.id}"
    )

    return task.id


@celery_app.task()
def cleanup_expired_cache() -> dict:  # type: ignore
    """清理过期缓存

    Returns:
        清理结果统计
    """
    try:
        import asyncio
        from app.services.cache.url.cache import ImageURLCache

        # 在Celery中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        cache = ImageURLCache()
        start_time = datetime.utcnow()

        # 清理过期缓存
        cleaned_count = loop.run_until_complete(cache.cleanup_expired())

        loop.close()

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "success": True,
            "cleaned_count": cleaned_count,
            "duration": duration,
            "timestamp": start_time.isoformat(),
        }

        logger.info(
            f"Expired cache cleanup completed: {cleaned_count} items cleaned, "
            f"duration: {duration:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to cleanup expired cache: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@celery_app.task()
def pre_refresh_active_urls() -> dict:  # type: ignore
    """预刷新活跃URL

    主动刷新即将过期的URL，提高缓存命中率
    """
    try:
        from app.services.cache.url.cache import ImageURLCache

        cache = ImageURLCache()
        start_time = datetime.utcnow()

        # 获取即将过期的URL（15分钟内）
        threshold = datetime.utcnow() + timedelta(minutes=15)
        # 简化为空列表，实际实现需要从缓存中查询
        expiring_urls: List[str] = []

        if not expiring_urls:
            return {
                "success": True,
                "count": 0,
                "message": "No expiring URLs to refresh",
                "duration": 0.0,
            }

        # 批量刷新
        job = group(
            refresh_url_cache.s(url) for url in expiring_urls
        )

        result = job.apply_async()
        results = result.get(timeout=120)

        success_count = sum(1 for r in results if r.get("success"))
        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "success": True,
            "total": len(expiring_urls),
            "success_count": success_count,
            "failed_count": len(expiring_urls) - success_count,
            "duration": duration,
            "timestamp": start_time.isoformat(),
        }

        logger.info(
            f"Pre-refresh completed: {success_count}/{len(expiring_urls)} "
            f"refreshed successfully, duration: {duration:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to pre-refresh active URLs: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
