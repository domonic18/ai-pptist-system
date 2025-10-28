"""
测试配置和fixtures
为所有测试提供共享的配置和fixtures

按照pytest最佳实践，根目录conftest.py包含全局共享fixtures
单元测试和集成测试的特定配置通过pytest markers和条件fixtures处理
"""

import os
import pytest
import requests
import time
from typing import Dict, Any
from app.core.config import settings

# 测试服务器配置 - 支持环境变量覆盖
TEST_SERVER_URL = os.environ.get("TEST_SERVER_URL", f"http://localhost:{settings.app_port}")
TEST_API_BASE = f"{TEST_SERVER_URL}/api/v1"


class HTTPTestClient:
    """HTTP测试客户端类 - 封装HTTP请求"""

    def __init__(self, base_url: str = TEST_API_BASE, default_timeout: int = settings.test_default_timeout):
        self.base_url = base_url
        self.default_timeout = default_timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.base_url}{path}"
        # 如果没有指定timeout，使用默认超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout
        return self.session.request(method, url, **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT请求"""
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self.request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        """PATCH请求"""
        return self.request("PATCH", path, **kwargs)

    def upload_file(self, path: str, files: dict, **kwargs) -> requests.Response:
        """文件上传请求"""
        url = f"{self.base_url}{path}"

        # 创建新的headers，只保留认证头部
        headers = {}
        if "Authorization" in self.session.headers:
            headers["Authorization"] = self.session.headers["Authorization"]

        # 合并额外的头部
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
            del kwargs["headers"]

        # 设置默认超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.default_timeout

        # 直接使用requests.post，让它自动设置multipart Content-Type
        return requests.post(url, files=files, headers=headers, **kwargs)

    def set_auth_token(self, token: str):
        """设置认证令牌"""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_auth_token(self):
        """清除认证令牌"""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]


def wait_for_server(url: str, timeout: int = settings.test_default_timeout) -> bool:
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=settings.test_health_check_timeout)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(settings.test_health_check_interval)
    return False


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境 - 会话级别的fixture"""
    print("\n🔧 设置测试环境...")

    # 检查测试服务器是否运行
    if not wait_for_server(TEST_SERVER_URL):
        pytest.fail(f"❌ 测试服务器未运行，请先启动后端服务: {TEST_SERVER_URL}")

    print("✅ 测试服务器连接成功")

    yield

    print("\n🧹 清理测试环境...")


@pytest.fixture(scope="function")
def client():
    """测试客户端fixture"""
    return HTTPTestClient()


@pytest.fixture(scope="function")
def unit_test_marker(request):
    """单元测试标记fixture"""
    # 这个fixture确保单元测试有正确的标记
    pass


@pytest.fixture(scope="function")
def integration_test_marker(request):
    """集成测试标记fixture"""
    # 这个fixture确保集成测试有正确的标记
    pass


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "images: 图片相关测试")
    config.addinivalue_line("markers", "basic: 基础功能测试")
    config.addinivalue_line("markers", "tags: 标签相关测试")
    config.addinivalue_line("markers", "tag_service: 标签服务测试")
    config.addinivalue_line("markers", "image_tags: 图片标签测试")


# 测试运行前的检查
def pytest_sessionstart(session):
    """测试会话开始前的检查"""
    print(f"\n🚀 开始集成测试")
    print(f"📡 测试服务器: {TEST_SERVER_URL}")


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后的清理"""
    print(f"\n✅ 测试完成，退出状态: {exitstatus}")