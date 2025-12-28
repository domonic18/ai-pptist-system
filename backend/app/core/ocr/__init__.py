"""
OCR服务模块
提供多种OCR引擎的统一接口
"""

from app.core.ocr.tencent_ocr_sdk_engine import TencentOCRSDKEngine
from app.core.ocr.baidu_ocr_engine import BaiduOCREngine
from app.core.ocr.multimodal_ocr_engine import MultimodalOCREngine
from app.core.ocr.hybrid_ocr_fusion import HybridOCRFusion
from app.core.ocr.mineru_adapter import MinerUAdapter

__all__ = [
    "TencentOCRSDKEngine",
    "BaiduOCREngine",
    "MultimodalOCREngine",
    "HybridOCRFusion",
    "MinerUAdapter",
]
