import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


class TestAPI:
    """API 接口单元测试"""

    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_get_conversation_empty(self, client):
        response = client.get("/api/conversation/nonexistent_thread")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_knowledge_stats(self, client):
        response = client.get("/api/knowledge/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "document_count" in data["result"]
