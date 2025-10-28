"""
腾讯云MetaInsight API客户端
实现MetaInsight图像检索API的HTTP调用
"""

import json
import time
import hashlib
import hmac
import aiohttp
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from app.core.config import settings
from app.core.log_utils import get_logger
from .text_preprocessor import preprocessor

logger = get_logger(__name__)


class MetaInsightAPIClient:
    """腾讯云MetaInsight API客户端"""

    def __init__(self):
        self.secret_id = settings.cos_secret_id
        self.secret_key = settings.cos_secret_key
        self.region = settings.cos_region
        self.app_id = self._extract_app_id_from_bucket()
        self.dataset_name = settings.meta_insight_dataset_name
        self.timeout = settings.meta_insight_timeout

        # API基础URL
        self.base_url = f"https://{self.app_id}.ci.{self.region}.myqcloud.com"

        # 验证配置
        if not all([self.secret_id, self.secret_key, self.region, self.app_id]):
            logger.warning("MetaInsight API配置不完整")

    def _extract_app_id_from_bucket(self) -> str:
        """从bucket名称中提取APP ID"""
        bucket = settings.cos_bucket
        if bucket and "-" in bucket:
            # bucket格式通常为 bucketname-appid
            return bucket.split("-")[-1]
        return ""

    def _generate_authorization(self, method: str, uri: str, params: Dict[str, Any] = None) -> str:
        """
        生成腾讯云API签名
        参考: https://cloud.tencent.com/document/product/436/7778
        """
        try:
            # 当前时间戳
            now = int(time.time())

            # 签名有效期（1小时）
            key_time = f"{now};{now + 3600}"

            # Step 1: 生成 SignKey
            sign_key = hmac.new(
                self.secret_key.encode('utf-8'),
                key_time.encode('utf-8'),
                hashlib.sha1
            ).hexdigest()

            # Step 2: 生成 UrlParamList 和 HttpParameters
            if params:
                sorted_params = sorted(params.items())
                url_param_list = ';'.join([k.lower() for k, v in sorted_params])
                http_parameters = urlencode(sorted_params)
            else:
                url_param_list = ""
                http_parameters = ""

            # Step 3: 生成 HeaderList 和 HttpHeaders
            headers = {
                'host': f"{self.app_id}.ci.{self.region}.myqcloud.com"
            }
            sorted_headers = sorted(headers.items())
            header_list = ';'.join([k.lower() for k, v in sorted_headers])
            http_headers = '&'.join([f"{k.lower()}={v}" for k, v in sorted_headers])

            # Step 4: 生成 HttpString
            http_string = f"{method.lower()}\n{uri}\n{http_parameters}\n{http_headers}\n"

            # Step 5: 生成 StringToSign
            string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"

            # Step 6: 生成 Signature
            signature = hmac.new(
                sign_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).hexdigest()

            # Step 7: 生成 Authorization
            authorization = (
                f"q-sign-algorithm=sha1&"
                f"q-ak={self.secret_id}&"
                f"q-sign-time={key_time}&"
                f"q-key-time={key_time}&"
                f"q-header-list={header_list}&"
                f"q-url-param-list={url_param_list}&"
                f"q-signature={signature}"
            )

            return authorization

        except Exception as e:
            logger.error(f"生成签名失败: {e}")
            raise

    async def search_by_text(
        self,
        text: str,
        limit: int = 10,
        match_threshold: int = 80,
        preprocess_strategy: str = "smart_truncate"
    ) -> List[Dict[str, Any]]:
        """
        使用文本描述进行图像检索

        Args:
            text: 检索文本描述，例如"包含一颗大树的图片"
            limit: 返回结果数量
            match_threshold: 匹配阈值
            preprocess_strategy: 文本预处理策略
                - "smart_truncate": 智能截断（默认）
                - "keywords_extract": 关键词提取
                - "simple_truncate": 简单截断

        Returns:
            检索结果列表
        """
        try:
            uri = "/datasetquery/imagesearch"

            # 预处理文本，确保符合MetaInsight API限制
            processed_text = preprocessor.preprocess_search_text(text, preprocess_strategy)

            # 构建请求体
            request_body = {
                "DatasetName": self.dataset_name,
                "Mode": "text",
                "Text": processed_text,
                "Limit": min(limit, settings.meta_insight_max_results),
                "MatchThreshold": match_threshold
            }

            # 生成签名
            authorization = self._generate_authorization("POST", uri)

            # 构建请求头
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": f"{self.app_id}.ci.{self.region}.myqcloud.com"
            }

            url = f"{self.base_url}{uri}"

            logger.info(
                "发起MetaInsight文本搜索请求",
                extra={
                    "original_text": text[:100],
                    "processed_text": processed_text,
                    "original_length": len(text),
                    "processed_length": len(processed_text),
                    "limit": limit,
                    "match_threshold": match_threshold,
                    "dataset": self.dataset_name,
                    "url": url,
                    "request_body": request_body,
                    "preprocess_strategy": preprocess_strategy
                }
            )

            # 发送HTTP请求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=json.dumps(request_body)
                ) as response:

                    response_text = await response.text()

                    if response.status == 200:
                        result = json.loads(response_text)
                        image_results = result.get("ImageResult", [])

                        logger.info(
                            "MetaInsight文本搜索成功",
                            extra={
                                "text": text[:100],
                                "results_count": len(image_results),
                                "request_id": result.get("RequestId"),
                                "full_response": result
                            }
                        )

                        return image_results
                    else:
                        logger.error(
                            "MetaInsight文本搜索失败",
                            extra={
                                "status_code": response.status,
                                "response": response_text[:500],
                                "text": text[:100]
                            }
                        )
                        return []

        except Exception as e:
            logger.error(
                "MetaInsight文本搜索异常",
                extra={
                    "text": text[:100],
                    "error": str(e)
                }
            )
            return []

    async def search_by_image(
        self,
        image_uri: str,
        limit: int = 10,
        match_threshold: int = 80
    ) -> List[Dict[str, Any]]:
        """
        使用图片进行图像检索（以图搜图）

        Args:
            image_uri: 图片COS URI，格式如: cos://bucket-appid/path/to/image.jpg
            limit: 返回结果数量
            match_threshold: 匹配阈值

        Returns:
            检索结果列表
        """
        try:
            uri = "/datasetquery/imagesearch"

            # 构建请求体
            request_body = {
                "DatasetName": self.dataset_name,
                "Mode": "pic",
                "URI": image_uri,
                "Limit": min(limit, settings.meta_insight_max_results),
                "MatchThreshold": match_threshold
            }

            # 生成签名
            authorization = self._generate_authorization("POST", uri)

            # 构建请求头
            headers = {
                "Authorization": authorization,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Host": f"{self.app_id}.ci.{self.region}.myqcloud.com"
            }

            url = f"{self.base_url}{uri}"

            logger.info(
                "发起MetaInsight图片搜索请求",
                extra={
                    "image_uri": image_uri,
                    "limit": limit,
                    "match_threshold": match_threshold,
                    "dataset": self.dataset_name,
                    "url": url,
                    "request_body": request_body
                }
            )

            # 发送HTTP请求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=json.dumps(request_body)
                ) as response:

                    response_text = await response.text()

                    if response.status == 200:
                        result = json.loads(response_text)
                        image_results = result.get("ImageResult", [])

                        logger.info(
                            "MetaInsight图片搜索成功",
                            extra={
                                "image_uri": image_uri,
                                "results_count": len(image_results),
                                "request_id": result.get("RequestId")
                            }
                        )

                        return image_results
                    else:
                        logger.error(
                            "MetaInsight图片搜索失败",
                            extra={
                                "status_code": response.status,
                                "response": response_text[:500],
                                "image_uri": image_uri
                            }
                        )
                        return []

        except Exception as e:
            logger.error(
                "MetaInsight图片搜索异常",
                extra={
                    "image_uri": image_uri,
                    "error": str(e)
                }
            )
            return []

    def _build_cos_uri(self, cos_key: str) -> str:
        """
        构建COS URI格式

        Args:
            cos_key: COS对象键

        Returns:
            COS URI，格式: cos://bucket-appid/path/to/file
        """
        bucket = settings.cos_bucket
        return f"cos://{bucket}/{cos_key}"

    async def health_check(self) -> bool:
        """
        检查MetaInsight服务健康状态

        Returns:
            服务是否健康
        """
        try:
            # 发送一个简单的搜索请求来检查服务状态
            await self.search_by_text("test", limit=1, match_threshold=90)
            return True  # 如果请求成功（即使没有结果），说明服务正常

        except Exception as e:
            logger.error(f"MetaInsight健康检查失败: {e}")
            return False