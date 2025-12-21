"""
AI Provider注册中心
管理所有Provider的注册
"""

from app.core.log_utils import get_logger
from .factory import AIProviderFactory
from .models import ModelCapability

logger = get_logger(__name__)


def register_all_providers():
    """注册所有Provider（按提供商组织）"""
    
    logger.info("开始注册所有AI Provider")
    
    # ===== Gemini提供商 =====
    try:
        from .providers.gemini.chat import GeminiChatProvider
        from .providers.gemini.vision import GeminiVisionProvider
        from .providers.gemini.imagen import ImagenProvider
        
        AIProviderFactory.register(ModelCapability.CHAT, "gemini", GeminiChatProvider)
        AIProviderFactory.register(ModelCapability.VISION, "gemini", GeminiVisionProvider)
        AIProviderFactory.register(ModelCapability.IMAGE_GEN, "gemini_imagen", ImagenProvider)
        
        logger.info("Gemini Provider注册完成")
    except ImportError as e:
        logger.warning(f"Gemini Provider注册失败: {e}")
    
    # ===== 通义千问 =====
    try:
        from .providers.qwen.chat import QwenChatProvider
        from .providers.qwen.image import QwenImageProvider
        
        AIProviderFactory.register(ModelCapability.CHAT, "qwen", QwenChatProvider)
        AIProviderFactory.register(ModelCapability.IMAGE_GEN, "qwen", QwenImageProvider)
        
        logger.info("通义千问 Provider注册完成")
    except ImportError as e:
        logger.warning(f"通义千问 Provider注册失败: {e}")
    
    # ===== 火山引擎 =====
    try:
        from .providers.volcengine_ark.image import VolcengineArkProvider
        
        AIProviderFactory.register(ModelCapability.IMAGE_GEN, "volcengine_ark", VolcengineArkProvider)
        
        logger.info("火山引擎 Provider注册完成")
    except ImportError as e:
        logger.warning(f"火山引擎 Provider注册失败: {e}")
    
    # ===== Nano Banana =====
    try:
        from .providers.nano_banana.image import NanoBananaProvider
        
        AIProviderFactory.register(ModelCapability.IMAGE_GEN, "nano_banana", NanoBananaProvider)
        
        logger.info("Nano Banana Provider注册完成")
    except ImportError as e:
        logger.warning(f"Nano Banana Provider注册失败: {e}")
    
    # ===== OpenAI兼容（跨提供商） =====
    try:
        from .providers.openai_compatible.chat import OpenAICompatibleChatProvider
        from .providers.openai_compatible.vision import OpenAICompatibleVisionProvider
        
        AIProviderFactory.register(ModelCapability.CHAT, "openai_compatible", OpenAICompatibleChatProvider)
        AIProviderFactory.register(ModelCapability.VISION, "openai_compatible", OpenAICompatibleVisionProvider)
        
        logger.info("OpenAI兼容 Provider注册完成")
    except ImportError as e:
        logger.warning(f"OpenAI兼容 Provider注册失败: {e}")
    
    logger.info(
        "所有AI Provider注册完成",
        operation="register_all_providers_complete",
        total_capabilities=len(AIProviderFactory._providers)
    )

