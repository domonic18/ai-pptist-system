#!/usr/bin/env python3
"""
单元测试运行脚本
专门用于运行单元测试，设置独立的环境配置
"""

import os
import sys
import subprocess


def main():
    """主函数"""
    # 设置单元测试环境变量
    env = os.environ.copy()
    env["UNIT_TESTING"] = "true"
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

    # 构建pytest命令 - 只运行单元测试
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",           # 只运行unit目录下的测试
        "-m", "unit",            # 只运行标记为unit的测试
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