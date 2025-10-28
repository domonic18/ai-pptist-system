"""
配置工具模块
处理配置加载、路径计算等工具方法
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)  


def get_project_root() -> Path:
    """获取项目根目录路径"""
    return Path(__file__).parent.parent.parent.parent


def load_env_file(env_file_path: Path, required_vars: Optional[List[str]] = None) -> bool:
    """加载环境变量文件"""
    if env_file_path.exists():
        try:
            logger.info(f"加载环境变量文件: {env_file_path}")
            with open(env_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # 如果环境变量中不存在该配置，才从文件加载
                        if key not in os.environ:
                            os.environ[key] = value
            return True
        except Exception as e:
            logger.warning(f"加载环境变量文件失败 {env_file_path}: {e}")

    # 检查是否设置了必要的环境变量
    if required_vars:
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.warning(f"缺少必要的环境变量: {missing_vars}")

    return False


def get_workspace_path(sub_path: str = "") -> Path:
    """获取workspace目录路径"""
    workspace_dir = get_project_root() / "workspace"
    if sub_path:
        return workspace_dir / sub_path
    return workspace_dir


def get_backend_path(sub_path: str = "") -> Path:
    """获取backend目录路径"""
    backend_dir = get_project_root() / "backend"
    if sub_path:
        return backend_dir / sub_path
    return backend_dir


def get_config_path(sub_path: str = "") -> Path:
    """获取config目录路径"""
    config_dir = get_project_root() / "config"
    if sub_path:
        return config_dir / sub_path
    return config_dir


def parse_list_config(value: str, separator: str = ",") -> List[str]:
    """解析逗号分隔的配置字符串为列表"""
    if not value:
        return []
    return [item.strip().lower() for item in value.split(separator)]


def parse_json_config(value: str) -> List[str]:
    """解析JSON格式的配置字符串"""
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.warning(f"JSON配置解析失败: {value}")
        return []


def ensure_directory_exists(path: Path) -> None:
    """确保目录存在，不存在则创建"""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {path}")