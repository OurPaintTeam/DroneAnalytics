"""Тестовые конфигурации — не используются в продакшене"""

# Авторизация
TEST_AUTH_USERNAME = "test_user"
TEST_AUTH_PASSWORD = "test_password_123"
TEST_API_KEY = "test-api-key-do-not-use-in-prod"

# JWT и безопасность
TEST_SECRET_KEY = b"test-secret-key-32-chars-long!!"  # Минимум 32 байта
TEST_JWT_ALGORITHM = "HS256"
TEST_ACCESS_TTL_SECONDS = 300  # 5 минут
TEST_REFRESH_TTL_SECONDS = 3600  # 1 час

# Прочее
TEST_CORS_ORIGINS = ["http://localhost:3000", "http://test.local"]
TEST_PASSWORD_SALT = "test-salt-value"