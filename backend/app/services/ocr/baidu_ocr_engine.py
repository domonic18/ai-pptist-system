"""
百度云OCR引擎服务
使用百度云HTTP API进行图片文字识别
"""

import base64
import os
from typing import List, Dict, Optional
from urllib.parse import urlencode
import httpx

from app.core.log_utils import get_logger
from app.core.storage import get_storage_service, download_image_by_key

logger = get_logger(__name__)

# 百度云OCR配置
BAIDU_OCR_API_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
BAIDU_OAUTH_URL = "https://aip.baidubce.com/oauth/2.0/token"


class BaiduOCREngine:
    """
    百度云OCR引擎

    使用百度云HTTP API进行图片文字识别
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        初始化百度云OCR引擎

        Args:
            api_key: 百度云API Key（如不传则从环境变量读取）
            secret_key: 百度云Secret Key（如不传则从环境变量读取）
        """
        self.api_key = api_key or os.getenv("BAIDU_OCR_API_KEY")
        self.secret_key = secret_key or os.getenv("BAIDU_OCR_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "百度云OCR凭证未配置，请设置BAIDU_OCR_API_KEY和BAIDU_OCR_SECRET_KEY环境变量"
            )

        # Access token缓存
        self._access_token: Optional[str] = None

        logger.info("百度云OCR引擎初始化成功")

    async def _get_access_token(self) -> str:
        """
        获取百度云Access Token

        使用AK，SK生成鉴权签名

        Returns:
            str: access_token
        """
        if self._access_token:
            return self._access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(BAIDU_OAUTH_URL, params=params)
            response.raise_for_status()
            result = response.json()

            if "access_token" not in result:
                raise Exception(f"获取Access Token失败: {result}")

            self._access_token = result["access_token"]
            logger.info("百度云Access Token获取成功")

            return self._access_token

    async def parse_from_cos_key(
        self,
        cos_key: str
    ) -> List[Dict]:
        """
        从COS Key解析图片

        使用统一下载方式下载图片并转为Base64后识别

        Args:
            cos_key: 图片的COS Key
        """
        try:
            logger.info("开始从COS Key进行百度云OCR识别", extra={"cos_key": cos_key})

            # 1. 使用统一的下载方式下载图片
            storage = get_storage_service()
            image_data, image_format = await download_image_by_key(cos_key, storage)

            logger.info(
                "图片下载成功",
                extra={
                    "cos_key": cos_key,
                    "image_size": len(image_data),
                    "format": image_format
                }
            )

            # 2. 转换为base64
            img_base64 = base64.b64encode(image_data).decode()

            logger.info(
                "图片转码完成",
                extra={
                    "cos_key": cos_key,
                    "base64_length": len(img_base64)
                }
            )

            # 3. 调用OCR API
            result = await self._call_ocr_api(img_base64)

            logger.info(
                "百度云OCR识别完成（COS Key）",
                extra={"cos_key": cos_key, "text_count": len(result)}
            )

            return result

        except Exception as e:
            logger.error(
                "百度云OCR识别失败（COS Key）",
                extra={"cos_key": cos_key, "error": str(e)}
            )
            raise

    async def parse_from_base64(
        self,
        img_base64: str
    ) -> List[Dict]:
        """
        从Base64编码解析图片

        Args:
            img_base64: 图片的base64编码
        """
        try:
            logger.info("开始从Base64进行百度云OCR识别")

            # 预处理 base64 字符串：移除 data:image/xxx;base64, 前缀（如果存在）
            if "," in img_base64:
                img_base64 = img_base64.split(",")[1]
            
            # 移除换行符和空格
            img_base64 = img_base64.replace("\n", "").replace("\r", "").replace(" ", "").strip()

            # 调用OCR API
            result = await self._call_ocr_api(img_base64)

            logger.info(
                "百度云OCR识别完成（Base64）",
                extra={"text_count": len(result)}
            )

            return result

        except Exception as e:
            logger.error("百度云OCR识别失败（Base64）", extra={"error": str(e)})
            raise

    async def _call_ocr_api(self, img_base64: str) -> List[Dict]:
        """
        调用百度云OCR API

        Args:
            img_base64: 图片的base64编码

        Returns:
            List[Dict]: 识别结果列表
        """
        # 获取access token
        access_token = await self._get_access_token()

        # 构建请求URL
        url = f"{BAIDU_OCR_API_URL}?access_token={access_token}"

        # 构建请求参数
        # 按照用户提供的官方示例补充所有参数
        payload = {
            "image": img_base64,
            "recognize_granularity": "big",
            "detect_direction": "false",
            "vertexes_location": "false",
            "paragraph": "false",
            "probability": "false",
            "char_probability": "false",
            "multidirectional_recognize": "false"
        }

        # 按照官方示例构建 Headers
        # 注意：用户示例中 Authorization 传的是 API_KEY
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 记录调试信息（截断Base64以防日志过大）
        logger.debug(
            "准备调用百度云OCR API",
            extra={
                "url": url,
                "base64_len": len(img_base64),
                "base64_head": img_base64[:50],
                "payload_keys": list(payload.keys())
            }
        )

        try:
            # 使用 trust_env=False 避开可能的代理干扰
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                # 显式进行 urlencode 并编码为 bytes，模拟 requests 的行为
                encoded_body = urlencode(payload).encode("utf-8")
                
                response = await client.post(
                    url,
                    headers=headers,
                    content=encoded_body
                )
                
                # 记录详细的响应信息
                logger.debug(
                    "百度云OCR API响应结果",
                    extra={
                        "status_code": response.status_code,
                        "response_body": response.text[:1000] # 记录更多内容
                    }
                )
                
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP请求异常: {str(e)}")
            raise Exception(f"请求百度云OCR接口失败: {str(e)}")

        # 检查错误
        if "error_code" in result:
            error_msg = result.get("error_msg", "未知错误")
            error_code = result.get("error_code")
            
            # 如果是格式错误，输出更多上下文
            if error_code == 216201:
                logger.error(
                    "百度云OCR返回图片格式错误",
                    extra={
                        "base64_len": len(img_base64),
                        "base64_head": img_base64[:100],
                        "payload_head": urlencode(payload)[:200]
                    }
                )
                
            raise Exception(f"百度云OCR API错误 [{error_code}]: {error_msg}")

        # 格式化结果
        return self._format_ocr_response(result)

    def _format_ocr_response(self, response: Dict) -> List[Dict]:
        """
        格式化百度云OCR API响应结果

        Args:
            response: 百度云OCR API响应

        Returns:
            List[Dict]: 格式化后的识别结果
        """
        formatted = []

        # 检查是否有识别结果
        words_result = response.get("words_result", [])
        if not words_result:
            logger.warning("百度云OCR未检测到文字")
            return formatted

        for item in words_result:
            # 获取文字内容
            text = item.get("words", "")

            # 获取位置信息
            location = item.get("location", {})
            if not location:
                continue

            bbox = {
                "x": location.get("left", 0),
                "y": location.get("top", 0),
                "width": location.get("width", 0),
                "height": location.get("height", 0)
            }

            # 获取置信度（如果有）
            probability = item.get("probability")
            confidence = 0.95
            if probability:
                confidence = probability.get("average", 0.95) / 100

            formatted.append({
                "text": text,
                "bbox": bbox,
                "confidence": confidence
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
