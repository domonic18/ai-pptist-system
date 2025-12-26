"""
MinerU OCR适配器
提供MinerU API调用和结果格式化功能
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import zipfile
import io
import httpx
from PIL import Image

from app.core.config.config import settings
from app.core.log_utils import get_logger
from app.core.storage import get_storage_service

logger = get_logger(__name__)


class MinerUAdapter:
    """
    MinerU OCR适配器

    提供MinerU API调用功能：
    1. 提交识别任务
    2. 查询任务状态
    3. 下载并解析识别结果
    4. 格式化为标准格式
    """

    def __init__(self):
        """初始化MinerU适配器"""
        self.api_url = settings.MINERU_API_URL
        self.token = settings.MINERU_TOKEN
        self.model_version = settings.MINERU_MODEL_VERSION
        self.timeout = settings.MINERU_TIMEOUT
        self.timeout_submit = settings.MINERU_TIMEOUT_SUBMIT
        self.timeout_poll = settings.MINERU_TIMEOUT_POLL
        self.timeout_download = settings.MINERU_TIMEOUT_DOWNLOAD
        self.timeout_image_size = settings.MINERU_TIMEOUT_IMAGE_SIZE
        self.max_retries = settings.MINERU_MAX_RETRIES
        self.storage_service = get_storage_service()

    async def recognize_from_cos_key(
        self,
        cos_key: str,
        enable_ocr: bool = True,
        enable_formula: bool = True,
        enable_table: bool = True
    ) -> List[Dict[str, Any]]:
        """
        从COS Key识别图片

        Args:
            cos_key: 图片COS Key
            enable_ocr: 是否开启OCR
            enable_formula: 是否识别公式
            enable_table: 是否识别表格

        Returns:
            List[Dict]: 识别结果列表（content_list.json格式）
        """
        start_time = datetime.now()

        try:
            # 步骤1: 获取图片URL
            image_url = await self._get_image_url(cos_key)

            logger.info(
                "开始MinerU识别",
                extra={
                    "cos_key": cos_key,
                    "enable_ocr": enable_ocr,
                    "enable_formula": enable_formula,
                    "enable_table": enable_table
                }
            )

            # 步骤2: 提交MinerU任务
            task_id = await self._submit_task(
                image_url=image_url,
                enable_ocr=enable_ocr,
                enable_formula=enable_formula,
                enable_table=enable_table
            )

            logger.info("MinerU任务已提交", extra={"task_id": task_id})

            # 步骤3: 轮询任务状态
            result = await self._poll_result(task_id)

            # 步骤4: 下载并解析ZIP文件
            content_list = await self._download_and_parse(result["full_zip_url"])

            # 步骤5: 获取原始图片尺寸
            image_size = await self._get_image_size(cos_key)

            # 步骤6: 添加图片尺寸到元数据
            parse_time = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.info(
                "MinerU识别完成",
                extra={
                    "task_id": task_id,
                    "content_count": len(content_list),
                    "parse_time_ms": parse_time,
                    "image_width": image_size["width"],
                    "image_height": image_size["height"]
                }
            )

            # 返回带尺寸信息的结果
            return {
                "content_list": content_list,
                "image_width": image_size["width"],
                "image_height": image_size["height"],
                "parse_time_ms": parse_time
            }

        except Exception as e:
            logger.error("MinerU识别失败", extra={"cos_key": cos_key, "error": str(e)})
            raise

    async def _get_image_url(self, cos_key: str) -> str:
        """
        获取图片的预签名URL

        注意：MinerU可能需要较长时间处理，所以过期时间设置较长（24小时）

        Args:
            cos_key: 图片COS Key

        Returns:
            str: 预签名URL
        """
        try:
            # 设置较长的过期时间，确保MinerU有足够时间处理
            # 24小时 = 86400秒
            url = await self.storage_service.generate_url(cos_key, expires=86400, operation="get")

            # 记录预签名URL信息（不记录完整URL以避免日志过大）
            logger.info(
                "成功生成COS预签名URL",
                extra={
                    "cos_key": cos_key,
                    "url_prefix": url[:100] + "..." if len(url) > 100 else url,
                    "expires_seconds": 86400
                }
            )

            return url
        except Exception as e:
            logger.error("获取图片URL失败", extra={"cos_key": cos_key, "error": str(e)})
            raise

    async def _submit_task(
        self,
        image_url: str,
        enable_ocr: bool,
        enable_formula: bool,
        enable_table: bool
    ) -> str:
        """
        提交识别任务到MinerU API

        Args:
            image_url: 待识别图片的URL
            enable_ocr: 是否开启OCR
            enable_formula: 是否识别公式
            enable_table: 是否识别表格

        Returns:
            str: MinerU任务ID
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        request_data = {
            "url": image_url,
            "model_version": self.model_version,
            "is_ocr": enable_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table
        }

        # 记录提交的请求信息（包含完整URL用于调试）
        logger.info(
            "提交MinerU识别任务",
            extra={
                "api_url": self.api_url,
                "image_url_length": len(image_url),
                "image_url_preview": image_url[:200] + "..." if len(image_url) > 200 else image_url,
                "image_url_full": image_url,  # 完整URL用于调试
                "model_version": self.model_version,
                "enable_ocr": enable_ocr,
                "enable_formula": enable_formula,
                "enable_table": enable_table
            }
        )

        async with httpx.AsyncClient(timeout=self.timeout_submit) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=request_data
            )
            response.raise_for_status()
            result = response.json()

            # 记录API响应
            logger.info(
                "MinerU任务提交响应",
                extra={
                    "response_code": result.get("code"),
                    "response_msg": result.get("msg"),
                    "response_data": result.get("data"),
                    "full_response": result  # 完整响应用于调试
                }
            )

            if result.get("code") != 0:
                logger.error(
                    "MinerU API返回错误",
                    extra={
                        "code": result.get("code"),
                        "msg": result.get("msg")
                    }
                )
                raise Exception(f"MinerU API error: {result.get('msg')}")

            task_id = result["data"]["task_id"]
            logger.info("MinerU任务提交成功", extra={"task_id": task_id})
            return task_id

    async def _poll_result(self, task_id: str) -> Dict[str, Any]:
        """
        轮询MinerU任务状态

        Args:
            task_id: MinerU任务ID

        Returns:
            Dict: 任务结果数据
        """
        status_url = f"{self.api_url.replace('/extract/task', '')}/extract/task/{task_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        max_attempts = int(self.timeout / 5)  # 每5秒轮询一次
        attempt = 0

        async with httpx.AsyncClient(timeout=self.timeout_poll) as client:
            while attempt < max_attempts:
                try:
                    response = await client.get(status_url, headers=headers)
                    response.raise_for_status()
                    result = response.json()

                    # 记录完整的API响应用于调试
                    logger.info(
                        "MinerU状态查询响应",
                        extra={
                            "task_id": task_id,
                            "attempt": attempt,
                            "response_code": result.get("code"),
                            "response_msg": result.get("msg"),
                            "data": result.get("data"),
                            "full_response": result  # 完整响应用于调试
                        }
                    )

                    if result.get("code") == 0:
                        data = result.get("data", {})
                        state = data.get("state")

                        if state == "done":
                            logger.info("MinerU任务完成", extra={"task_id": task_id})
                            return data
                        elif state == "failed":
                            error_msg = data.get("err_msg", "Unknown error")
                            error_code = data.get("err_code", "UNKNOWN")
                            logger.error(
                                "MinerU任务失败",
                                extra={
                                    "task_id": task_id,
                                    "error_code": error_code,
                                    "error_msg": error_msg,
                                    "full_data": data
                                }
                            )
                            raise Exception(f"MinerU task failed: {error_msg} (code: {error_code})")
                        elif state == "running":
                            # 处理中，记录进度
                            progress = data.get("extract_progress", {})
                            extracted = progress.get("extracted_pages", 0)
                            total = progress.get("total_pages", 0)
                            logger.debug(
                                "MinerU任务处理中",
                                extra={
                                    "task_id": task_id,
                                    "progress": f"{extracted}/{total}"
                                }
                            )
                    else:
                        logger.warning(
                            "MinerU API返回非成功状态码",
                            extra={
                                "task_id": task_id,
                                "code": result.get("code"),
                                "msg": result.get("msg")
                            }
                        )

                except httpx.HTTPStatusError as e:
                    logger.warning("轮询MinerU状态失败", extra={"attempt": attempt, "error": str(e)})

                attempt += 1
                await asyncio.sleep(5)

        raise Exception(f"MinerU task timeout after {self.timeout} seconds")

    async def _download_and_parse(self, zip_url: str) -> List[Dict[str, Any]]:
        """
        下载并解析ZIP文件

        Args:
            zip_url: ZIP文件下载链接

        Returns:
            List[Dict]: content_list.json内容
        """
        async with httpx.AsyncClient(timeout=self.timeout_download) as client:
            response = await client.get(zip_url)
            response.raise_for_status()

            # 解析ZIP文件
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))

            # 读取content_list.json
            try:
                with zip_file.open("content_list.json") as f:
                    import json
                    content_list = json.load(f)
                    return content_list
            except KeyError:
                raise Exception("ZIP文件中未找到content_list.json")

    async def _get_image_size(self, cos_key: str) -> Dict[str, int]:
        """
        获取图片尺寸

        Args:
            cos_key: 图片COS Key

        Returns:
            Dict: {width, height}
        """
        try:
            # 获取预签名URL
            url = await self.storage_service.generate_url(cos_key, expires=3600, operation="get")

            # 下载图片
            async with httpx.AsyncClient(timeout=self.timeout_image_size) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 使用PIL读取尺寸
                image = Image.open(io.BytesIO(response.content))
                return {
                    "width": image.width,
                    "height": image.height
                }

        except Exception as e:
            logger.error("获取图片尺寸失败", extra={"cos_key": cos_key, "error": str(e)})
            # 返回默认尺寸
            return {
                "width": 1920,
                "height": 1080
            }

    def format_mineru_result(
        self,
        mineru_data: Dict[str, Any],
        cos_key: str
    ) -> Dict[str, Any]:
        """
        格式化MinerU结果为标准格式

        Args:
            mineru_data: MinerU返回的数据
            cos_key: 图片COS Key

        Returns:
            Dict: 格式化后的结果
        """
        content_list = mineru_data.get("content_list", [])
        image_width = mineru_data.get("image_width", 1920)
        image_height = mineru_data.get("image_height", 1080)

        # 分离文字和图片区域
        text_regions = []
        image_regions = []

        for item in content_list:
            item_type = item.get("type")
            bbox = item.get("bbox", [0, 0, 0, 0])

            # 转换bbox格式 [x0, y0, x1, y1] -> {x, y, width, height}
            if len(bbox) == 4:
                x0, y0, x1, y1 = bbox
                bbox_dict = {
                    "x": x0,
                    "y": y0,
                    "width": x1 - x0,
                    "height": y1 - y0
                }
            else:
                bbox_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

            if item_type in ["text", "title"]:
                # 文字区域
                text_regions.append({
                    "text": item.get("text", ""),
                    "bbox": bbox_dict,
                    "type": item_type
                })
            elif item_type == "image":
                # 图片/装饰元素
                image_regions.append({
                    "img_path": item.get("img_path", ""),
                    "bbox": bbox_dict,
                    "type": "decoration"
                })

        return {
            "text_regions": text_regions,
            "image_regions": image_regions,
            "metadata": {
                "engine": "mineru",
                "image_width": image_width,
                "image_height": image_height,
                "cos_key": cos_key,
                "parse_time_ms": mineru_data.get("parse_time_ms", 0)
            }
        }


# ============================================================================
# 辅助函数
# ============================================================================

def convert_bbox_from_normalized(
    bbox: List[int],
    image_width: int,
    image_height: int
) -> Dict[str, int]:
    """
    将归一化bbox(0-1000)转换为像素坐标

    Args:
        bbox: [x0, y0, x1, y1] (0-1000范围)
        image_width: 图片宽度
        image_height: 图片高度

    Returns:
        Dict: {x, y, width, height}
    """
    if len(bbox) != 4:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    x0, y0, x1, y1 = bbox

    # 从0-1000转换为像素坐标
    x = int((x0 / 1000) * image_width)
    y = int((y0 / 1000) * image_height)
    width = int(((x1 - x0) / 1000) * image_width)
    height = int(((y1 - y0) / 1000) * image_height)

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height
    }
