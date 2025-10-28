"""
图片生成业务处理器
处理图片生成的业务逻辑和异常处理
"""

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.image.image_generation_service import ImageGenerationService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class ImageGenerationHandler:
    """图片生成业务处理器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.image_generation_service = ImageGenerationService(db)

    async def handle_generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图片生成请求

        Args:
            request_data: 生成请求参数

        Returns:
            Dict[str, Any]: 处理结果

        Raises:
            HTTPException: 请求处理失败时抛出HTTP异常
        """
        try:
            # 验证输入参数
            prompt = request_data.get("prompt", "")
            if not prompt or not prompt.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="提示词不能为空"
                )

            # 提取参数
            model_name = request_data.get("model_name", "dall-e-3")
            width = request_data.get("width", 1024)
            height = request_data.get("height", 1024)
            quality = request_data.get("quality", "standard")
            style = request_data.get("style", "vivid")

            logger.info("处理图片生成请求", extra={
                "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "model_name": model_name,
                "width": width,
                "height": height
            })

            # 调用服务生成图片
            result = await self.image_generation_service.generate_image(
                prompt=prompt.strip(),
                model_name=model_name,
                width=width,
                height=height,
                quality=quality,
                style=style
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error("图片生成请求处理异常", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"图片生成失败: {str(e)}"
            )

  