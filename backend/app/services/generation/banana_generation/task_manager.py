"""
Banana任务状态管理器
负责管理Redis中的任务状态，供前端轮询查询
"""

import json
from datetime import datetime
from typing import Dict, Optional
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class BananaTaskManager:
    """
    Banana任务状态管理器

    职责：
    1. Celery Worker 生成图片完成后，保存图片URL到Redis
    2. 前端轮询时，从Redis获取所有页面状态和COS图片URL
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    async def update_slide_status(
        self,
        task_id: str,
        slide_index: int,
        status: str,
        image_url: Optional[str] = None,
        **kwargs
    ):
        """
        更新单页状态（由 Celery Worker 调用）

        Args:
            task_id: 任务ID
            slide_index: 幻灯片索引
            status: 状态 (pending | processing | completed | failed)
            image_url: COS图片URL（生成完成后传入）
            **kwargs: 其他信息（generation_time, cos_path, error等）
        """
        key = f"banana:task:{task_id}:slide:{slide_index}"

        # 明确验证COS URL格式
        if image_url and not self._is_valid_cos_url(image_url):
            logger.warning(
                f"潜在问题：图片URL可能不符合COS规范: {image_url}. "
                f"建议格式: https://{{bucket}}.cos.{{region}}.myqcloud.com/ai-generated/ppt/..."
            )

        data = {
            "index": slide_index,
            "status": status,
            "image_url": image_url,  # COS图片URL
            "updated_at": datetime.utcnow().isoformat(),
            **kwargs
        }

        # 保存到Redis（1小时过期）
        await self.redis.set(
            key,
            json.dumps(data),
            expire=3600
        )

        logger.info("更新幻灯片状态", extra={
            "task_id": task_id,
            "slide_index": slide_index,
            "status": status,
            "has_image_url": bool(image_url)
        })

        # 更新任务总进度
        await self._update_task_progress(task_id)

    async def _update_task_progress(self, task_id: str):
        """
        更新任务总进度（聚合所有页面状态）（前端轮询时的数据源）
        
        Args:
            task_id: 任务ID
        """
        # 从Redis获取任务信息（包括总页数）
        task_info_key = f"banana:task:{task_id}:info"
        task_info_str = await self.redis.get(task_info_key)

        if not task_info_str:
            logger.warning(f"任务信息未找到: {task_id}")
            return

        try:
            task_info = json.loads(task_info_str)
            total_slides = task_info.get("total_slides")
            
            if total_slides is None:
                logger.warning(f"任务信息中缺少total_slides: {task_id}")
                return
        except json.JSONDecodeError as e:
            logger.error(f"无法解析任务信息: {task_id}, 错误: {e}")
            return

        # 查询所有幻灯片的状态
        slides_data = []
        completed_count = 0
        failed_count = 0
        processing_count = 0

        for i in range(total_slides):
            key = f"banana:task:{task_id}:slide:{i}"
            slide_data_str = await self.redis.get(key)

            if slide_data_str:
                slide_data = json.loads(slide_data_str)
                slides_data.append(slide_data)

                if slide_data["status"] == "completed":
                    completed_count += 1
                elif slide_data["status"] == "failed":
                    failed_count += 1
                elif slide_data["status"] == "processing":
                    processing_count += 1
            else:
                # 还未开始的页面
                slides_data.append({
                    "index": i,
                    "status": "pending",
                    "image_url": None
                })

        # 判断总任务状态
        if completed_count + failed_count == total_slides:
            overall_status = "completed"  # 全部完成（包括失败的）
        elif processing_count > 0 or completed_count > 0:
            overall_status = "processing"  # 有页面正在处理或已完成
        else:
            overall_status = "pending"  # 都还没开始

        # 保存总进度（新格式：将计数信息嵌套在progress对象下）
        progress_key = f"banana:task:{task_id}:progress"
        progress_data = {
            "task_id": task_id,
            "status": overall_status,
            "progress": {
                "total": total_slides,
                "completed": completed_count,
                "failed": failed_count,
                "pending": total_slides - completed_count - failed_count - processing_count
            },
            "slides": slides_data,  # 包含所有页面的状态和COS图片URL
            "updated_at": datetime.utcnow().isoformat()
        }

        await self.redis.set(
            progress_key,
            json.dumps(progress_data),
            expire=3600
        )

        logger.info("更新任务总进度", extra={
            "task_id": task_id,
            "status": overall_status,
            "completed": completed_count,
            "failed": failed_count,
            "total": total_slides
        })

    async def get_task_progress(self, task_id: str) -> Optional[Dict]:
        """
        获取任务进度（前端轮询时调用）

        Returns:
            包含所有页面状态和COS图片URL的字典
        """
        key = f"banana:task:{task_id}:progress"
        data = await self.redis.get(key)

        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"Redis数据解析失败: {e}")
                return None
        else:
            # 如果Redis中没有，返回初始状态（新格式）
            return {
                "task_id": task_id,
                "status": "pending",
                "progress": {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "pending": 0
                },
                "slides": []
            }

    def _is_valid_cos_url(self, url: str) -> bool:
        """
         简要验证腾讯云 COS URL 格式

        Minimal validation for Tencent Cloud COS URL format.
        Only checks basic URL structure and myqcloud.com domain.
        """
        if not url.startswith('https://'):
            return False

        # Check domain contains myqcloud.com
        try:
            domain = url.split('/')[2]
            return 'myqcloud.com' in domain
        except Exception:
            return False
