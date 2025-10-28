#!/usr/bin/env python3
"""
完整测试运行脚本
运行所有测试（单元测试 + 集成测试）
"""

import os
import sys
import subprocess


def main():
    """主函数"""
    # 设置测试环境变量
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["APP_DEBUG"] = "true"
    env["LOG_LEVEL"] = "ERROR"

    # 使用内存数据库
    env["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Mock COS配置
    env["COS_SECRET_ID"] = "test-secret-id"
    env["COS_SECRET_KEY"] = "test-secret-key"
    env["COS_REGION"] = "test-region"
    env["COS_BUCKET"] = "test-bucket"
    env["COS_SCHEME"] = "https"

    # 构建pytest命令 - 运行所有测试
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",               # 运行所有测试
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