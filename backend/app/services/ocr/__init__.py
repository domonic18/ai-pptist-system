"""
OCR服务模块
提供多种OCR引擎的统一接口
"""

from app.services.ocr.tencent_ocr_sdk_engine import TencentOCRSDKEngine

__all__ = [
    "TencentOCRSDKEngine",
]
