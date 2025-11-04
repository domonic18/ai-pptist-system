"""
AI生成图片存储服务
处理AI生成图片并存储到COS和数据库的业务逻辑
"""

import uuid
import time
import base64
import aiohttp
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.image import ImageRepository
from app.schemas.image_manager import ImageCreate, ImageGenerationAndStoreRequest
from app.core.storage import get_storage_service
from app.core.config import settings
from app.services.image.image_generation_service import ImageGenerationService
from app.core.log_utils import get_logger
from app.utils.id_utils import generate_short_id

logger = get_logger(__name__)


class ImageGenerationStoreService:
    """AI生成图片存储服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ImageRepository(db)
        self.storage_service = get_storage_service()
        self.generation_service = ImageGenerationService(db)

    async def generate_and_store_image(
        self,
        request: ImageGenerationAndStoreRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        生成图片并存储到COS和数据库

        Args:
            request: 图片生成和存储请求
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            logger.info(
                "开始AI生成图片并存储",
                extra={
                    "prompt": request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
                    "model_name": request.generation_model,
                    "user_id": user_id,
                    "width": request.width,
                    "height": request.height
                }
            )

            # 1. 调用AI生成图片
            generation_result = await self.generation_service.generate_image(
                prompt=request.prompt,
                model_name=request.generation_model,
                width=request.width,
                height=request.height,
                quality=request.quality,
                style=request.style
            )

            if not generation_result.get("success"):
                return {
                    "success": False,
                    "message": "图片生成失败",
                    "error": generation_result.get("error", "未知错误")
                }

            # 2. 获取生成的图片URL
            image_url = generation_result["image"]["url"]
            model_name = generation_result["image"]["model"]

            logger.info("获取AI生成图片信息", extra={
                "model_name": model_name,
                "image_url_length": len(image_url),
                "is_base64": image_url.startswith('data:image/'),
                "image_url_preview": image_url[:100] + "..." if len(image_url) > 100 else image_url
            })

            # 3. 尝试下载图片内容
            image_content = await self._download_image_from_url(image_url)
            cos_key = None
            final_image_url = image_url

            if image_content:
                # 4. 获取内容成功，上传到COS
                cos_key = self._generate_ai_storage_key(request.generation_model, user_id)

                # 检测MIME类型
                upload_mime_type = "image/png"
                if image_url.startswith('data:image/'):
                    upload_mime_type = image_url.split(';')[0].split(':')[1]

                try:
                    upload_result = await self.storage_service.upload(
                        image_content, cos_key, upload_mime_type
                    )

                    # 生成预签名URL用于图片访问
                    try:
                        presigned_url = await self.storage_service.generate_url(
                            cos_key,
                            expires=3600,  # 1小时有效期
                            operation="get"
                        )
                        final_image_url = presigned_url
                        logger.info("图片已上传到COS并生成预签名URL", extra={
                            "cos_key": cos_key,
                            "presigned_url": presigned_url,
                            "file_size": upload_result.size
                        })
                    except Exception as url_error:
                        logger.warning(f"生成预签名URL失败，使用原始COS URL", extra={
                            "url_error": str(url_error),
                            "cos_key": cos_key
                        })
                        final_image_url = upload_result.url

                except Exception as upload_error:
                    logger.warning(f"COS上传失败，使用原始URL", extra={"upload_error": str(upload_error)})
                    cos_key = None
            else:
                # 下载失败，使用原始URL
                logger.warning("图片下载失败，使用原始URL", extra={
                    "image_url_length": len(image_url),
                    "image_url_preview": image_url[:100] + "..." if len(image_url) > 100 else image_url
                })

            # 6. 创建数据库记录
            file_size = len(image_content) if image_content else 0

            # 检测MIME类型
            mime_type = "image/png"
            if image_url.startswith('data:image/'):
                # 从base64 data URL中提取MIME类型
                mime_type = image_url.split(';')[0].split(':')[1]

            image_data = ImageCreate(
                prompt=request.prompt,
                description=request.description or f"AI生成图片 - {request.prompt[:50]}...",
                tags=request.tags or ["AI生成"],
                is_public=request.is_public,
                image_url=final_image_url,  # 存储预签名URL供前端直接使用
                cos_key=cos_key,
                cos_bucket=settings.cos_bucket if cos_key else None,
                cos_region=settings.cos_region if cos_key else None,
                source_type="generated",
                generation_model=model_name,
                width=request.width,
                height=request.height,
                file_size=file_size,
                mime_type=mime_type,
                original_filename=f"ai_generated_{uuid.uuid4().hex[:8]}.{mime_type.split('/')[1]}"
            )

            image = await self.repository.create_image(image_data, user_id)

            storage_info = "COS存储" if cos_key else "原始URL引用"
            logger.info(
                "AI生成图片记录创建成功",
                extra={
                    "image_id": image.id,
                    "cos_key": cos_key,
                    "model_name": model_name,
                    "file_size": file_size,
                    "storage_type": storage_info
                }
            )

            return {
                "success": True,
                "image_id": image.id,
                "image_url": final_image_url,
                "cos_key": cos_key,
                "message": f"AI生成图片成功（{storage_info}）"
            }

        except Exception as e:
            logger.error(f"AI生成图片并存储失败: {e}")
            return {
                "success": False,
                "message": "AI生成图片并存储失败",
                "error": str(e)
            }

    async def _download_image_from_url(self, image_url: str) -> Optional[bytes]:
        """
        从URL下载图片内容或处理base64图片数据

        Args:
            image_url: 图片URL或base64数据

        Returns:
            Optional[bytes]: 图片内容，失败返回None
        """
        try:
            # 检查是否是base64图片数据
            if image_url.startswith('data:image/'):
                return self._decode_base64_image(image_url)

            # 检查URL长度
            if len(image_url) > 2048:  # 大多数服务器的URL长度限制
                logger.error(
                    f"图片URL过长，无法下载",
                    extra={
                        "image_url_length": len(image_url),
                        "image_url_preview": image_url[:100] + "..." if len(image_url) > 100 else image_url
                    }
                )
                return None

            timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)  # 增加超时时间
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                logger.info(f"开始下载图片", extra={"image_url_length": len(image_url)})

                async with session.get(image_url) as response:
                    response.raise_for_status()

                    # 检查响应内容类型
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        logger.error(f"响应内容不是图片格式", extra={"content_type": content_type})
                        return None

                    # 读取内容
                    content = await response.read()

                    # 检查内容大小
                    if len(content) == 0:
                        logger.error("下载的图片内容为空")
                        return None

                    if len(content) > 10 * 1024 * 1024:  # 10MB限制
                        logger.error(f"图片文件过大", extra={"content_length": len(content)})
                        return None

                    logger.info(f"图片下载成功", extra={
                        "content_length": len(content),
                        "content_type": content_type
                    })
                    return content

        except aiohttp.ClientTimeout as e:
            logger.error(f"下载图片超时", extra={"error": str(e), "image_url_length": len(image_url)})
            return None
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP请求失败", extra={
                "status_code": e.status,
                "error": str(e),
                "image_url_length": len(image_url)
            })
            return None
        except aiohttp.ClientError as e:
            logger.error(f"客户端请求错误", extra={
                "error": str(e),
                "image_url_length": len(image_url)
            })
            return None
        except Exception as e:
            logger.error(f"获取图片失败", extra={
                "error": str(e),
                "image_url_length": len(image_url),
                "image_url_preview": image_url[:100] + "..." if len(image_url) > 100 else image_url
            })
            return None

    def _decode_base64_image(self, data_url: str) -> Optional[bytes]:
        """
        解码base64图片数据

        Args:
            data_url: base64图片数据URL，格式如 data:image/png;base64,iVBORw0KGgo...

        Returns:
            Optional[bytes]: 解码后的图片内容，失败返回None
        """
        try:
            logger.info("开始解码base64图片数据", extra={"data_url_length": len(data_url)})

            # 解析data URL格式
            if not data_url.startswith('data:image/'):
                logger.error("不是有效的图片data URL格式")
                return None

            # 查找逗号分隔符
            comma_index = data_url.find(',')
            if comma_index == -1:
                logger.error("data URL格式错误，缺少逗号分隔符")
                return None

            # 提取MIME类型和base64数据
            header = data_url[:comma_index]
            base64_data = data_url[comma_index + 1:]

            # 检查是否包含base64标识
            if ';base64' not in header:
                logger.error("data URL不包含base64标识")
                return None

            # 解码base64数据
            image_content = base64.b64decode(base64_data)

            # 检查解码结果
            if len(image_content) == 0:
                logger.error("base64解码结果为空")
                return None

            # 检查文件大小
            if len(image_content) > 10 * 1024 * 1024:  # 10MB限制
                logger.error(f"base64图片数据过大", extra={"content_length": len(image_content)})
                return None

            # 提取MIME类型
            mime_type = header.split(';')[0].split(':')[1]
            logger.info(f"base64图片解码成功", extra={
                "content_length": len(image_content),
                "mime_type": mime_type
            })

            return image_content

        except base64.binascii.Error as e:
            logger.error(f"base64解码失败", extra={"error": str(e)})
            return None
        except Exception as e:
            logger.error(f"处理base64图片数据失败", extra={"error": str(e)})
            return None

    def _generate_ai_storage_key(self, model_name: str, user_id: str) -> str:
        """
        生成AI图片的COS存储键

        Args:
            model_name: 模型名称
            user_id: 用户ID

        Returns:
            str: COS存储键
        """
        # 清理模型名称，移除特殊字符
        safe_model_name = "".join(c for c in model_name if c.isalnum() or c in ('-', '_')).lower()
        timestamp = int(time.time())
        unique_id = generate_short_id()

        # 构建存储键：ai_generated/{model_name}/{user_id}/{timestamp}_{unique_id}.png
        return f"ai_generated/{safe_model_name}/{user_id}/{timestamp}_{unique_id}.png"