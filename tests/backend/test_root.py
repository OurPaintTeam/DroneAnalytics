import pytest

class TestRootEndpoint:
    """Тесты для GET /"""

    def test_root_returns_hello(self, client):
        """R1: GET / возвращает приветствие"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Hello, FastAPI!"}

    def test_root_post_not_allowed(self, client):
        """R2: POST на GET-эндпоинт возвращает 405"""
        response = client.post("/")
        
        assert response.status_code == 405
        assert response.json().get("detail") == "Method Not Allowed"