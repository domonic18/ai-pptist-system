"""
模块导入测试
测试所有模块的导入是否正常
"""

import pytest


@pytest.mark.unit
@pytest.mark.imports
class TestModuleImports:
    """模块导入测试类"""

    def test_config_import(self):
        """测试配置模块导入"""
        from app.core.config import settings
        assert settings is not None

    def test_database_import(self):
        """测试数据库模块导入"""
        from app.db.database import engine, AsyncSessionLocal
        assert engine is not None
        assert AsyncSessionLocal is not None

    def test_model_import(self):
        """测试图片模型导入"""
        from app.models.image import Image
        assert Image is not None

    def test_service_imports(self):
        """测试服务模块导入"""
        from app.services.image.management_service import ManagementService
        from app.core.storage import COSStorage
        from app.services.image.upload_service import ImageUploadService
        assert ManagementService is not None
        assert COSStorage is not None
        assert ImageUploadService is not None

    def test_api_imports(self):
        """测试API模块导入"""
        from app.api.v1.endpoints.image_manager import router as images_router
        from app.api.v1.endpoints.image_upload import router as image_upload_router
        from app.api.v1.router import api_router
        assert images_router is not None
        assert image_upload_router is not None
        assert api_router is not None