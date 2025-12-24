"""
腾讯云OCR引擎服务
使用腾讯云Python SDK进行图片文字识别
"""

import base64
import json
import os
from typing import List, Dict, Optional
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models as ocr_models

from app.core.log_utils import get_logger
from app.core.storage import get_storage_service

logger = get_logger(__name__)


class TencentOCRSDKEngine:
    """
    腾讯云OCR引擎 - SDK版本

    使用腾讯云OCR API进行图片文字识别
    """

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "ap-guangzhou"
    ):
        """
        初始化腾讯云OCR引擎

        Args:
            secret_id: 腾讯云SecretId（如不传则从环境变量读取）
            secret_key: 腾讯云SecretKey（如不传则从环境变量读取）
            region: 地域，默认ap-guangzhou
        """
        self.secret_id = secret_id or os.getenv("TENCENT_OCR_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENT_OCR_SECRET_KEY")
        self.region = region or os.getenv("TENCENT_OCR_REGION", "ap-guangzhou")

        if not self.secret_id or not self.secret_key:
            raise ValueError(
                "腾讯云OCR凭证未配置，请设置TENCENT_OCR_SECRET_ID和TENCENT_OCR_SECRET_KEY环境变量"
            )

        # 创建凭证
        cred = credential.Credential(self.secret_id, self.secret_key)

        # 配置HTTP选项
        httpProfile = HttpProfile()
        httpProfile.endpoint = "ocr.tencentcloudapi.com"

        # 配置客户端选项
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        # 创建SDK客户端
        self.client = ocr_client.OcrClient(cred, self.region, clientProfile)

        logger.info("腾讯云OCR引擎初始化成功", extra={"region": self.region})

    async def parse_from_cos_key(
        self,
        cos_key: str,
        use_enhanced: bool = True
    ) -> List[Dict]:
        """
        从COS Key解析图片

        通过统一存储服务从COS拉取图片，然后进行OCR识别

        Args:
            cos_key: 图片COS Key（如：ai-generated/ppt/xxx/slide_0.png）
            use_enhanced: 是否使用增强版识别（默认True，推荐使用）

        Returns:
            List[Dict]: 识别结果列表
        """
        try:
            logger.info("开始OCR识别", extra={"cos_key": cos_key})

            # 1. 通过统一存储服务从COS拉取图片
            storage = get_storage_service()
            download_result = await storage.download(cos_key)

            # 2. 直接转换为base64，不做任何预处理
            img_base64 = base64.b64encode(download_result.data).decode()

            logger.info(
                "图片数据准备完成",
                extra={
                    "cos_key": cos_key,
                    "data_size": len(download_result.data),
                    "base64_size": len(img_base64)
                }
            )

            # 3. 调用OCR API
            result = await self._call_accurate_ocr(img_base64)

            logger.info(
                "OCR识别完成",
                extra={"cos_key": cos_key, "text_count": len(result)}
            )

            return result

        except Exception as e:
            logger.error("OCR识别失败", extra={"cos_key": cos_key, "error": str(e)})
            raise

    async def _call_accurate_ocr(self, img_base64: str) -> List[Dict]:
        """
        调用增强印刷体识别（GeneralAccurateOCR）

        使用from_json_string方式设置参数，与腾讯云API示例一致

        Args:
            img_base64: 图片的base64编码

        Returns:
            List[Dict]: 识别结果列表
        """
        # 构建请求参数（与腾讯云API示例完全一致）
        params = {
            "ImageBase64": img_base64,
            "IsWords": True,
            "EnableDetectSplit": True,
            "IsPdf": False,
            "EnableDetectText": True,
            "ConfigID": "OCR"
        }

        # 创建请求对象并使用from_json_string设置参数
        req = ocr_models.GeneralAccurateOCRRequest()
        req.from_json_string(json.dumps(params))

        # 调用API
        resp = self.client.GeneralAccurateOCR(req)

        # 格式化结果
        return self._format_ocr_response(resp)

    def _format_ocr_response(self, resp) -> List[Dict]:
        """
        格式化OCR API响应结果

        Args:
            resp: 腾讯云OCR API响应

        Returns:
            List[Dict]: 格式化后的识别结果
        """
        formatted = []

        # 检查是否有错误
        if hasattr(resp, 'Error') and resp.Error:
            raise Exception(f"OCR API错误: {resp.Error.Message}")

        # 检查是否有识别结果
        if not hasattr(resp, 'TextDetections') or not resp.TextDetections:
            logger.warning("OCR未检测到文字")
            return formatted

        for item in resp.TextDetections:
            # 获取边界框
            polygon = item.Polygon
            if polygon:
                # 计算矩形边界框（从多边形顶点计算）
                bbox = {
                    "x": int(min(p.X for p in polygon)),
                    "y": int(min(p.Y for p in polygon)),
                    "width": int(max(p.X for p in polygon) - min(p.X for p in polygon)),
                    "height": int(max(p.Y for p in polygon) - min(p.Y for p in polygon))
                }
            else:
                # 使用ItemCoord作为备选
                bbox = {
                    "x": item.ItemCoord.X,
                    "y": item.ItemCoord.Y,
                    "width": item.ItemCoord.Width,
                    "height": item.ItemCoord.Height
                }

            formatted.append({
                "text": item.DetectedText,
                "bbox": bbox,
                "confidence": item.Confidence / 100 if item.Confidence else 0.95
            })

        return formatted

    def infer_font_size(self, bbox: Dict) -> int:
        """
        根据边界框推断字体大小

        Args:
            bbox: 边界框坐标

        Returns:
            int: 推断的字体大小
        """
        estimated_size = int(bbox["height"] * 0.75)
        return max(12, min(72, estimated_size))

    def infer_font_weight(self, text: str, bbox: Dict) -> str:
        """
        推断字重（粗体/常规）

        Args:
            text: 文字内容
            bbox: 边界框坐标

        Returns:
            str: "bold" 或 "normal"
        """
        # 简单规则：文字少且高度大的可能是标题（粗体）
        if len(text) < 20 and bbox.get("height", 0) > 40:
            return "bold"
        return "normal"
