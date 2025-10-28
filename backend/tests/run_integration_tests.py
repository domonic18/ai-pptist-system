#!/usr/bin/env python3
"""
集成测试运行脚本
专门用于运行集成测试，设置独立的环境配置
"""

import os
import sys
import subprocess


def main():
    """主函数"""
    # 设置集成测试环境变量
    env = os.environ.copy()
    env["INTEGRATION_TESTING"] = "true"
    env["TESTING"] = "true"
    env["APP_DEBUG"] = "true"
    env["LOG_LEVEL"] = "ERROR"

    # 集成测试使用开发环境配置
    # 优先加载开发环境配置文件
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", ".env.local")
    if os.path.exists(env_file_path):
        print(f"加载开发环境配置: {env_file_path}")
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    else:
        print("警告: 开发环境配置文件 .env.local 不存在")
        print("将使用默认开发环境配置")
        env["DATABASE_URL"] = "postgresql+asyncpg://ai_pptist_dev:dev_password@localhost:5432/ai_pptist_dev"
        env["POSTGRES_USER"] = "ai_pptist_dev"
        env["POSTGRES_PASSWORD"] = "dev_password"
        env["POSTGRES_DB"] = "ai_pptist_dev"
        env["REDIS_URL"] = "redis://localhost:6379/0"

    # 构建pytest命令 - 只运行集成测试
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/interface/",      # 只运行interface目录下的测试
        "-m", "integration",     # 只运行标记为integration的测试
        "-v",
        "--tb=short"
    ]

    # 添加额外的参数
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    # 运行测试
    result = subprocess.run(cmd, env=env, cwd=os.path.dirname(os.path.dirname(__file__)))

    # 返回测试结果
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()