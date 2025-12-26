"""
MinerU OCR适配器
提供MinerU API调用和结果格式化功能
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import zipfile
import io
import httpx
import uuid
import mimetypes
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
    ) -> Dict[str, Any]:
        """
        从COS Key识别图片

        Args:
            cos_key: 图片COS Key
            enable_ocr: 是否开启OCR
            enable_formula: 是否识别公式
            enable_table: 是否识别表格

        Returns:
            Dict: 识别结果（包含content_list、image_width、image_height、image_cos_keys等）
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

            # 步骤4: 下载并解析ZIP文件，同时上传图片到COS
            # 使用原始cos_key作为前缀来组织存储
            cos_key_prefix = f"{settings.cos_temp_prefix}/mineru_images/{cos_key.replace('/', '_')}"
            content_list, image_cos_keys = await self._download_and_parse(
                result["full_zip_url"],
                cos_key_prefix=cos_key_prefix
            )

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
                    "image_height": image_size["height"],
                    "extracted_images": len(image_cos_keys)
                }
            )

            # 返回带尺寸和COS key信息的结果
            return {
                "content_list": content_list,
                "image_width": image_size["width"],
                "image_height": image_size["height"],
                "parse_time_ms": parse_time,
                "image_cos_keys": image_cos_keys
            }

        except Exception as e:
            logger.error("MinerU识别失败", extra={"cos_key": cos_key, "error": str(e)})
            raise

    async def _get_image_url(self, cos_key: str) -> str:
        """
        获取图片的访问URL

        根据配置选择使用公开URL或预签名URL：
        - 公开URL：简短但需要COS设置为公有读私有写
        - 预签名URL：长但支持COS私有读写

        Args:
            cos_key: 图片COS Key

        Returns:
            str: 图片URL
        """
        try:
            # 检查是否使用公开URL
            if settings.MINERU_USE_PUBLIC_URL:
                # 构建公开URL（简短，适合COS公有读私有写）
                public_url = self._build_public_url(cos_key)
                logger.info(
                    "使用COS公开URL",
                    extra={
                        "cos_key": cos_key,
                        "public_url": public_url,
                        "url_length": len(public_url)
                    }
                )
                return public_url
            else:
                # 使用预签名URL（长，但支持COS私有读写）
                # 设置较长的过期时间，确保MinerU有足够时间处理
                # 24小时 = 86400秒
                url = await self.storage_service.generate_url(cos_key, expires=86400, operation="get")

                logger.info(
                    "使用COS预签名URL",
                    extra={
                        "cos_key": cos_key,
                        "url_length": len(url)
                    }
                )

                return url
        except Exception as e:
            logger.error("获取图片URL失败", extra={"cos_key": cos_key, "error": str(e)})
            raise

    def _build_public_url(self, cos_key: str) -> str:
        """
        构建COS公开访问URL

        使用配置文件中的bucket和region构建公开URL

        Args:
            cos_key: 图片COS Key

        Returns:
            str: 公开URL
        """
        # 使用配置文件中的COS bucket和region
        bucket = settings.cos_bucket
        region = settings.cos_region
        scheme = settings.cos_scheme

        # 构建公开URL: https://{bucket}.cos.{region}.myqcloud.com/{cos_key}
        public_url = f"{scheme}://{bucket}.cos.{region}.myqcloud.com/{cos_key}"

        return public_url

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

                        # 根据MinerU API文档，状态可能是: pending/running/failed/success/done
                        if state in ("success", "done"):
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
                        elif state in ("pending", "running", "processing"):
                            # 处理中，记录进度
                            progress = data.get("extract_progress", {})
                            extracted = progress.get("extracted_pages", 0)
                            total = progress.get("total_pages", 0)
                            logger.debug(
                                "MinerU任务处理中",
                                extra={
                                    "task_id": task_id,
                                    "progress": f"{extracted}/{total}",
                                    "state": state
                                }
                            )
                        else:
                            logger.warning(
                                "MinerU API返回未知状态",
                                extra={
                                    "task_id": task_id,
                                    "state": state,
                                    "data": data
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

    async def _download_and_parse(
        self,
        zip_url: str,
        cos_key_prefix: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        下载并解析ZIP文件，并提取图片上传到COS

        Args:
            zip_url: ZIP文件下载链接
            cos_key_prefix: COS存储键前缀（用于组织图片存储）

        Returns:
            Tuple: (content_list.json内容, 图片路径到COS key的映射)
        """
        import json

        async with httpx.AsyncClient(timeout=self.timeout_download) as client:
            response = await client.get(zip_url)
            response.raise_for_status()

            # 解析ZIP文件
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))

            # 记录ZIP中的所有文件名（用于调试）
            file_list = zip_file.namelist()
            logger.info(
                "ZIP文件内容",
                extra={
                    "file_count": len(file_list),
                    "files": file_list[:10]  # 只记录前10个文件名
                }
            )

            # 查找content_list.json文件（支持带ID的命名格式）
            # 可能的命名格式：
            #   - content_list.json (无前缀)
            #   - {uuid}_content_list.json (UUID前缀，如: 7d84c8b1-057e-4d29-a646-9b9d36e42813_content_list.json)
            #   - content_list_{uuid}.json (UUID后缀，不太可能但保留兼容性)
            content_list_file = None
            for file_name in file_list:
                # 使用 "in" 检查而不是 "startswith"，因为UUID可能在前面
                if "content_list" in file_name and file_name.endswith(".json"):
                    content_list_file = file_name
                    logger.info(
                        "找到content_list文件",
                        extra={"file_name": file_name}
                    )
                    break

            if not content_list_file:
                logger.error(
                    "ZIP文件中未找到content_list.json",
                    extra={
                        "available_files": file_list,
                        "searched_pattern": "*content_list*.json"
                    }
                )
                raise Exception(f"ZIP文件中未找到content_list.json，可用文件: {file_list}")

            # 读取content_list文件
            try:
                with zip_file.open(content_list_file) as f:
                    content_list = json.load(f)
            except Exception as e:
                logger.error(
                    "解析content_list文件失败",
                    extra={
                        "file_name": content_list_file,
                        "error": str(e)
                    }
                )
                raise Exception(f"解析content_list文件失败: {str(e)}")

            # 提取并上传图片到COS
            image_path_to_cos_key = await self._extract_and_upload_images(
                zip_file, file_list, content_list, cos_key_prefix
            )

            return content_list, image_path_to_cos_key

    async def _extract_and_upload_images(
        self,
        zip_file: zipfile.ZipFile,
        file_list: List[str],
        content_list: List[Dict[str, Any]],
        cos_key_prefix: Optional[str] = None
    ) -> Dict[str, str]:
        """
        从ZIP中提取图片并上传到COS

        Args:
            zip_file: ZIP文件对象
            file_list: ZIP中的文件列表
            content_list: content_list.json内容
            cos_key_prefix: COS存储键前缀

        Returns:
            Dict: 图片路径到COS key的映射 {"images/xxx.jpg": "cos_key"}
        """
        image_path_to_cos_key = {}

        # 收集所有需要上传的图片路径
        image_paths = set()
        for item in content_list:
            if item.get("type") == "image":
                img_path = item.get("img_path")
                if img_path:
                    image_paths.add(img_path)

        if not image_paths:
            logger.info("content_list中没有图片需要上传")
            return image_path_to_cos_key

        logger.info(
            "开始上传ZIP中的图片到COS",
            extra={
                "image_count": len(image_paths),
                "image_paths": list(image_paths)
            }
        )

        # 上传每个图片
        for img_path in image_paths:
            try:
                # 检查文件是否在ZIP中
                if img_path not in file_list:
                    logger.warning(
                        "图片文件不在ZIP中",
                        extra={"img_path": img_path}
                    )
                    continue

                # 从ZIP中读取图片数据
                with zip_file.open(img_path) as img_file:
                    img_data = img_file.read()

                # 推断MIME类型
                mime_type, _ = mimetypes.guess_type(img_path)
                if not mime_type or not mime_type.startswith("image/"):
                    mime_type = "image/jpeg"

                # 生成COS存储键
                file_ext = self._get_file_extension(img_path, mime_type)
                unique_filename = f"{uuid.uuid4()}{file_ext}"

                if cos_key_prefix:
                    cos_key = f"{cos_key_prefix}/{unique_filename}"
                else:
                    cos_key = f"{settings.cos_temp_prefix}/mineru/{unique_filename}"

                # 上传到COS
                await self.storage_service.upload(
                    img_data, cos_key, mime_type
                )

                image_path_to_cos_key[img_path] = cos_key

                logger.info(
                    "图片上传成功",
                    extra={
                        "img_path": img_path,
                        "cos_key": cos_key,
                        "size": len(img_data)
                    }
                )

            except Exception as e:
                logger.error(
                    "上传图片失败",
                    extra={
                        "img_path": img_path,
                        "error": str(e)
                    }
                )
                # 继续处理其他图片，不中断整个流程
                continue

        logger.info(
            "图片上传完成",
            extra={
                "total": len(image_paths),
                "uploaded": len(image_path_to_cos_key),
                "failed": len(image_paths) - len(image_path_to_cos_key)
            }
        )

        return image_path_to_cos_key

    def _get_file_extension(self, img_path: str, mime_type: str) -> str:
        """
        从图片路径或MIME类型获取文件扩展名

        Args:
            img_path: 图片路径
            mime_type: MIME类型

        Returns:
            str: 文件扩展名（包含点）
        """
        # 首先尝试从路径获取
        if "." in img_path.split("/")[-1]:
            return "." + img_path.rsplit(".", 1)[-1].lower()

        # 从MIME类型映射
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff"
        }

        return mime_to_ext.get(mime_type, ".jpg")

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
            mineru_data: MinerU返回的数据（包含image_cos_keys）
            cos_key: 图片COS Key

        Returns:
            Dict: 格式化后的结果
        """
        content_list = mineru_data.get("content_list", [])
        image_width = mineru_data.get("image_width", 1920)
        image_height = mineru_data.get("image_height", 1080)
        image_cos_keys = mineru_data.get("image_cos_keys", {})

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
                img_path = item.get("img_path", "")
                image_region = {
                    "bbox": bbox_dict,
                    "type": "decoration"
                }

                # 优先使用COS key，如果没有则保留原始路径
                if img_path in image_cos_keys:
                    image_region["cos_key"] = image_cos_keys[img_path]
                    image_region["img_path"] = img_path  # 保留原始路径用于调试
                else:
                    # 如果没有上传成功，保留原始路径
                    image_region["img_path"] = img_path
                    logger.warning(
                        "图片未上传到COS，使用原始路径",
                        extra={"img_path": img_path}
                    )

                image_regions.append(image_region)

        return {
            "text_regions": text_regions,
            "image_regions": image_regions,
            "metadata": {
                "engine": "mineru",
                "image_width": image_width,
                "image_height": image_height,
                "cos_key": cos_key,
                "parse_time_ms": mineru_data.get("parse_time_ms", 0),
                "extracted_images_count": len(image_cos_keys)
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
