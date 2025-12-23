#!/usr/bin/env python3
"""
Banana 模板初始化脚本

功能：
1. 将本地模板图片上传到腾讯云 COS
2. 在数据库中创建模板记录

使用方法：
    cd backend
    python -m scripts.init_banana_templates

COS 路径结构：
    templates/banana/{template_id}.{ext}  - 模板原始图片
    templates/banana/{template_id}_cover.{ext}  - 模板缩略图

注意：运行前确保：
1. 配置正确的 COS 密钥和存储桶
2. 数据库已正确初始化
3. 本地模板图片文件存在于 frontend/public/templates/
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 在导入配置之前，先加载 .env.local 文件（如果存在）
# 优先加载 .env.local，如果不存在则使用 .env
from app.utils.config_utils import get_config_path, load_env_file

# 优先加载 .env.local（本地开发配置）
env_local_path = get_config_path(".env.local")
if env_local_path.exists():
    print(f"加载本地开发配置: {env_local_path}")
    load_env_file(env_local_path)
else:
    # 如果 .env.local 不存在，尝试加载 .env
    env_path = get_config_path(".env")
    if env_path.exists():
        print(f"加载默认配置: {env_path}")
        load_env_file(env_path)
    else:
        print("警告: 未找到配置文件 (.env.local 或 .env)")

from qcloud_cos import CosConfig, CosS3Client
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.repositories.banana_generation import BananaGenerationRepository
from app.core.log_utils import get_logger

logger = get_logger(__name__)

# 模板配置
TEMPLATE_CONFIGS = [
    {
        "id": "template_academic",
        "name": "学术风格",
        "description": "适用于学术报告、研究汇报等场景",
        "filename": "template_academic.jpg",
        "type": "system",
        "aspect_ratio": "16:9"
    },
    {
        "id": "template_b",
        "name": "商务风格",
        "description": "适用于商务演示、企业汇报等场景",
        "filename": "template_b.png",
        "type": "system",
        "aspect_ratio": "16:9"
    },
    {
        "id": "template_glass",
        "name": "玻璃质感",
        "description": "现代玻璃质感风格，适用于科技产品展示",
        "filename": "template_glass.png",
        "type": "system",
        "aspect_ratio": "16:9"
    },
    {
        "id": "template_s",
        "name": "简约风格",
        "description": "简约清新风格，适用于各类演示",
        "filename": "template_s.png",
        "type": "system",
        "aspect_ratio": "16:9"
    },
    {
        "id": "template_vector_illustration",
        "name": "矢量插画",
        "description": "矢量插画风格，适用于创意展示",
        "filename": "template_vector_illustration.png",
        "type": "system",
        "aspect_ratio": "16:9"
    },
    {
        "id": "template_y",
        "name": "优雅风格",
        "description": "优雅大气风格，适用于正式场合",
        "filename": "template_y.png",
        "type": "system",
        "aspect_ratio": "16:9"
    },
]

# COS 路径前缀
COS_TEMPLATE_PREFIX = "templates/banana"


def get_cos_client() -> CosS3Client:
    """创建 COS 客户端"""
    config = CosConfig(
        Region=settings.cos_region,
        SecretId=settings.cos_secret_id,
        SecretKey=settings.cos_secret_key,
        Token=None,
        Scheme='https'
    )
    return CosS3Client(config)


def upload_file_to_cos(
    cos_client: CosS3Client,
    local_path: str,
    cos_key: str
) -> str:
    """
    上传文件到 COS
    
    Args:
        cos_client: COS 客户端
        local_path: 本地文件路径
        cos_key: COS 存储键
        
    Returns:
        str: COS 访问 URL
    """
    # 确定 MIME 类型
    ext = os.path.splitext(local_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    content_type = mime_types.get(ext, 'image/png')
    
    # 上传文件
    with open(local_path, 'rb') as fp:
        response = cos_client.put_object(
            Bucket=settings.cos_bucket,
            Key=cos_key,
            Body=fp,
            ContentType=content_type
        )
    
    # 构建 URL
    cos_url = f"https://{settings.cos_bucket}.cos.{settings.cos_region}.myqcloud.com/{cos_key}"
    return cos_url


async def init_template(
    db: AsyncSession,
    cos_client: CosS3Client,
    template_config: dict,
    templates_dir: str
) -> bool:
    """
    初始化单个模板
    
    Args:
        db: 数据库会话
        cos_client: COS 客户端
        template_config: 模板配置
        templates_dir: 模板图片目录
        
    Returns:
        bool: 是否成功
    """
    template_id = template_config["id"]
    filename = template_config["filename"]
    local_path = os.path.join(templates_dir, filename)
    
    # 检查本地文件是否存在
    if not os.path.exists(local_path):
        logger.warning(f"模板文件不存在: {local_path}")
        return False
    
    try:
        repo = BananaGenerationRepository(db)
        
        # 检查模板是否已存在
        existing = await repo.get_template(template_id)
        if existing:
            logger.info(f"模板已存在，跳过: {template_id}")
            return True
        
        # 获取文件扩展名
        ext = os.path.splitext(filename)[1]
        
        # 构建 COS Key (存储相对路径)
        cos_key = f"{COS_TEMPLATE_PREFIX}/{template_id}{ext}"
        
        # 上传原始图片到 COS
        upload_file_to_cos(cos_client, local_path, cos_key)
        logger.info(f"上传模板图片成功: {cos_key}")
        
        # 创建数据库记录，存储 COS Key 而不是完整 URL
        template = await repo.create_template(
            template_id=template_id,
            name=template_config["name"],
            cover_url=cos_key,        # 存储 Key
            full_image_url=cos_key,   # 存储 Key
            template_type=template_config["type"],
            aspect_ratio=template_config["aspect_ratio"],
            description=template_config.get("description")
        )
        
        logger.info(f"创建模板记录成功: {template_id}")
        return True
        
    except Exception as e:
        logger.error(f"初始化模板失败 {template_id}: {str(e)}")
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("Banana 模板初始化脚本")
    print("=" * 60)
    
    # 检查 COS 配置
    if not settings.cos_secret_id or not settings.cos_secret_key:
        print("错误: COS 配置不完整，请检查环境变量")
        print("  - cos_secret_id")
        print("  - cos_secret_key")
        print("  - cos_bucket")
        print("  - cos_region")
        sys.exit(1)
    
    if not settings.cos_bucket:
        print("错误: COS bucket 未配置")
        sys.exit(1)
    
    print(f"COS 配置:")
    print(f"  - Region: {settings.cos_region}")
    print(f"  - Bucket: {settings.cos_bucket}")
    print(f"  - 路径前缀: {COS_TEMPLATE_PREFIX}")
    print()
    
    # 确定模板图片目录
    # 项目结构: backend/ 和 frontend/ 是同级目录
    workspace_root = project_root.parent
    templates_dir = os.path.join(workspace_root, "frontend", "public", "templates")
    
    if not os.path.exists(templates_dir):
        print(f"错误: 模板目录不存在: {templates_dir}")
        sys.exit(1)
    
    print(f"模板目录: {templates_dir}")
    print(f"待初始化模板数: {len(TEMPLATE_CONFIGS)}")
    print()
    
    # 创建 COS 客户端
    cos_client = get_cos_client()
    
    # 初始化所有模板
    success_count = 0
    fail_count = 0
    
    async with AsyncSessionLocal() as db:
        for config in TEMPLATE_CONFIGS:
            print(f"处理模板: {config['id']} ({config['name']})...")
            
            success = await init_template(db, cos_client, config, templates_dir)
            
            if success:
                success_count += 1
                print(f"  ✓ 成功")
            else:
                fail_count += 1
                print(f"  ✗ 失败")
    
    print()
    print("=" * 60)
    print(f"初始化完成: 成功 {success_count}, 失败 {fail_count}")
    print("=" * 60)
    
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

