"""
单页同步标注服务

遵循项目API设计规范:
- 业务逻辑处理
- 调用其他服务
- 错误处理
"""

from typing import Dict, Any
from app.services.annotation.service import AnnotationService
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class SingleAnnotationService:
    """
    单张幻灯片同步标注服务

    职责:
    - 处理单张幻灯片的同步标注
    - 直接返回标注结果（不创建异步任务）
    - 错误处理和日志记录
    """

    def __init__(self, annotation_service: AnnotationService):
        """
        初始化单页标注服务

        Args:
            annotation_service: 标注服务实例
        """
        self.annotation_service = annotation_service

    async def annotate_single_slide(
        self,
        slide_data: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        单张幻灯片同步标注

        Args:
            slide_data: 幻灯片数据（包含slide_id, screenshot, elements）
            model_config: 模型配置（model_id等）

        Returns:
            Dict[str, Any]: 标注结果

        Raises:
            Exception: 标注失败时抛出异常
        """
        try:
            logger.info(
                "开始单张幻灯片同步标注",
                extra={
                    "slide_id": slide_data.get("slide_id"),
                    "model_config": model_config
                }
            )

            # 调用分析服务进行标注
            # 注意：AnalysisService.analyze_slide 返回单个幻灯片的分析结果
            result = await self.annotation_service.analysis_service.analyze_slide(
                slide=slide_data,
                model_config=model_config
            )

            if result and result.get("status") == "success":
                logger.info(
                    "单张幻灯片标注完成",
                    extra={
                        "slide_id": slide_data.get("slide_id"),
                        "has_results": True,
                        "result_keys": list(result.keys()) if result else []
                    }
                )

                return result
            else:
                logger.error(
                    "单张幻灯片标注失败：返回结果为空或状态失败",
                    extra={
                        "slide_id": slide_data.get("slide_id"),
                        "result_status": result.get("status") if result else "no_result"
                    }
                )
                raise Exception(f"标注失败: {result.get('error', '未知错误')}" if result else "标注结果为空")

        except Exception as e:
            logger.error(
                "单张幻灯片同步标注失败",
                extra={
                    "slide_id": slide_data.get("slide_id"),
                    "error": str(e)
                }
            )
            raise Exception(f"单张幻灯片标注失败: {str(e)}")
