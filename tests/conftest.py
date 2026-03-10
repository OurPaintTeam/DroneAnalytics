"""
Общие фикстуры для ВСЕХ тестов (backend, frontend, integration).
Сейчас пустой, но здесь будут фикстуры, которые нужны везде.
"""
import pytest


@pytest.fixture(scope="session")
def test_run_id():
    """Уникальный ID для этого запуска тестов"""
    import uuid
    return str(uuid.uuid4())