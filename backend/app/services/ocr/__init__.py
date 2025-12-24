"""
OCR服务模块
提供多种OCR引擎的统一接口
"""

from app.services.ocr.tencent_ocr_sdk_engine import TencentOCRSDKEngine
from app.services.ocr.baidu_ocr_engine import BaiduOCREngine
from app.services.ocr.multimodal_ocr_engine import MultimodalOCREngine

__all__ = [
    "TencentOCRSDKEngine",
    "BaiduOCREngine",
    "MultimodalOCREngine",
]
