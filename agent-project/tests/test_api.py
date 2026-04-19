"""
FastAPI 接口单元测试
使用 FastAPI TestClient 模拟 HTTP 请求，验证各 API 接口的正确性。
测试覆盖：健康检查、根路径、对话历史查询、知识库统计。
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建 FastAPI 测试客户端，供所有测试方法共享"""
    from api.main import app
    return TestClient(app)


class TestAPI:
    """API 接口单元测试"""

    def test_health_check(self, client):
        """测试健康检查接口：应返回 200 和正常状态消息"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_root(self, client):
        """测试根路径：应返回 200 和 API 服务基本信息"""
        response = client.get("/")
        assert response.status_code == 200

    def test_get_conversation_empty(self, client):
        """测试查询不存在的会话：应返回 200 和空列表"""
        response = client.get("/api/conversation/nonexistent_thread")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_knowledge_stats(self, client):
        """测试知识库统计接口：应返回包含 document_count 字段的统计数据"""
        response = client.get("/api/knowledge/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "document_count" in data["result"]
