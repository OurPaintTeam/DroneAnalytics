"""
Тесты для эндпоинтов авторизации (POST /auth/login)
"""
import jwt
# Фикстуры (client, valid_credentials, etc.) импортируются автоматически из conftest.py

class TestAuthLogin:
    """Позитивные сценарии (успешный вход)"""

    def test_login_success_valid_credentials(self, client, valid_credentials, valid_expires_in):
        """A1: Успешный вход с валидными данными"""
        response = client.post("/auth/login", json=valid_credentials)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == valid_expires_in

    def test_login_success_min_username_length(self, client, valid_credentials):
        """A2: (граница min username = 4 символа)"""
        response = client.post("/auth/login", json={
            "username": "user",  # 4 символа
            "password": valid_credentials["password"]
        })
        
        assert response.status_code != 400

    def test_login_success_max_username_length(self, client, valid_credentials):
        """A3:(граница max username = 64 символа)"""
        response = client.post("/auth/login", json={
            "username": "a" * 64,  # 64 символа
            "password": valid_credentials["password"]
        })
        
        assert response.status_code != 400

    def test_login_success_min_password_length(self, client, valid_credentials):
        """A4:(граница min password = 8 символов)"""
        response = client.post("/auth/login", json={
            "username": valid_credentials["username"],
            "password": "password"  # 8 символов
        })
        
        assert response.status_code != 400

    def test_login_success_max_password_length(self, client, valid_credentials):
        """A5: (граница max password = 64 символа)"""
        response = client.post("/auth/login", json={
            "username": valid_credentials["username"],
            "password": "x" * 64  # 64 символа
        })

        assert response.status_code != 400

    def test_login_response_structure(self, client, valid_credentials):
        """A6: Проверка структуры ответа (все поля, типы данных)"""
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert isinstance(data["expires_in"], int)
        assert data["token_type"] == "Bearer"

    def test_login_different_tokens_per_request(self, client, valid_credentials):
        """A7: Каждый вход выдаёт новые уникальные токены"""
        response1 = client.post("/auth/login", json=valid_credentials)
        response2 = client.post("/auth/login", json=valid_credentials)
        
        tokens1 = response1.json()
        tokens2 = response2.json()
        
        assert tokens1["access_token"] != tokens2["access_token"]
        assert tokens1["refresh_token"] != tokens2["refresh_token"]

    def test_login_tokens_are_jwt(self, client, valid_credentials):
        """A8: Токены имеют формат JWT (три части)"""
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        assert data["access_token"].count(".") == 2
        assert data["refresh_token"].count(".") == 2

    def test_login_access_refresh_different(self, client, valid_credentials):
        """A9: Access и refresh токены — разные"""
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        assert data["access_token"] != data["refresh_token"]
    
    """Негативные сценарии (ошибки авторизации)"""
    def test_login_wrong_password(self, client, valid_credentials):
        """A10: Неверный пароль -> 401"""
        payload = {**valid_credentials, "password": "wrongpass"}
        response = client.post("/auth/login", json=payload)
        
        assert response.status_code == 401
        assert response.json()["code"] == 401
        assert "Invalid credentials" in response.json()["message"]

    def test_login_wrong_username(self, client, valid_credentials):
        """A11: Неверный логин -> 401"""
        payload = {**valid_credentials, "username": "unknown"}
        response = client.post("/auth/login", json=payload)
        
        assert response.status_code == 401
        assert response.json()["code"] == 401

    def test_login_wrong_username_and_password(self, client):
        """A12: Неверный логин и пароль -> 401"""
        response = client.post("/auth/login", json={
            "username": "unknown",
            "password": "wrongpass"
        })
        
        assert response.status_code == 401
        assert response.json()["code"] == 401

    """Валидация Pydantic-моделей"""
    def test_login_empty_username(self, client):
        """A13: Пустой username -> 400"""
        response = client.post("/auth/login", json={
            "username": "",
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_username_too_short(self, client):
        """A14: Username короче 4 символов -> 400"""
        response = client.post("/auth/login", json={
            "username": "usr",  # 3 символа
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_username_too_long(self, client):
        """A15: Username длиннее 64 символов -> 400"""
        response = client.post("/auth/login", json={
            "username": "a" * 65,  # 65 символов
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_empty_password(self, client):
        """A16: Пустой password -> 400"""
        response = client.post("/auth/login", json={
            "username": "user",
            "password": ""
        })
        
        assert response.status_code == 400

    def test_login_password_too_short(self, client):
        """A17: Password короче 8 символов -> 400"""
        response = client.post("/auth/login", json={
            "username": "user",
            "password": "1234567"  # 7 символов
        })
        
        assert response.status_code == 400

    def test_login_password_too_long(self, client):
        """A18: Password длиннее 64 символов -> 400"""
        response = client.post("/auth/login", json={
            "username": "user",
            "password": "x" * 65  # 65 символов
        })
        
        assert response.status_code == 400

    def test_login_missing_username(self, client):
        """A19: Отсутствует поле username -> 400"""
        response = client.post("/auth/login", json={
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_missing_password(self, client):
        """A20: Отсутствует поле password -> 400"""
        response = client.post("/auth/login", json={
            "username": "user"
        })
        
        assert response.status_code == 400

    def test_login_extra_field_forbidden(self, client, valid_credentials):
        """A21: Лишнее поле в JSON -> 400 (StrictModel)"""
        payload = {**valid_credentials, "extra_field": "should_fail"}
        response = client.post("/auth/login", json=payload)
        
        assert response.status_code == 400

    def test_login_username_wrong_type(self, client):
        """A22: Неверный тип данных username (int вместо str) -> 400"""
        response = client.post("/auth/login", json={
            "username": 123,
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_password_wrong_type(self, client):
        """A23: Неверный тип данных password (int вместо str) -> 400"""
        response = client.post("/auth/login", json={
            "username": "user",
            "password": 12345678
        })
        
        assert response.status_code == 400

    def test_login_username_null(self, client):
        """A24: Null вместо username -> 400"""
        response = client.post("/auth/login", json={
            "username": None,
            "password": "password123"
        })
        
        assert response.status_code == 400

    def test_login_password_null(self, client):
        """A25: Null вместо password -> 400"""
        response = client.post("/auth/login", json={
            "username": "user",
            "password": None
        })
        
        assert response.status_code == 400
    """ Тесты формата запроса"""

    def test_login_wrong_content_type(self, client, valid_credentials):
        """A26: Неверный Content-Type -> 400"""
        response = client.post(
            "/auth/login",
            json=valid_credentials,
            headers={"Content-Type": "text/plain"}
        )
        
        
        assert response.status_code == 400

    def test_login_malformed_json(self, client):
        """A27: Malformed JSON -> 400"""
        response = client.post(
            "/auth/login",
            content='{"invalid": json}',  # Невалидный JSON
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400

    def test_login_empty_body(self, client):
        """A28: Пустое тело запроса -> 400"""
        response = client.post(
            "/auth/login",
            json={}
        )
        
        assert response.status_code == 400

    def test_login_array_instead_of_object(self, client):
        """A29: Массив вместо объекта -> 400"""
        response = client.post(
            "/auth/login",
            json=[{"username": "user", "password": "password123"}]
        )
        
        assert response.status_code == 400

    def test_login_string_instead_of_object(self, client):
        """A30: Строка вместо объекта -> 400"""
        response = client.post(
            "/auth/login",
            json="not an object"
        )
        
        assert response.status_code == 400
    
    def test_login_access_token_claims(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
        """A31: Access токен содержит обязательные claims"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        # Декодируем токен (без проверки подписи — только структура)
        payload = jwt.decode(data["access_token"], valid_secret_key, algorithms=valid_jwt_algorithm)
        
        # Проверяем наличие обязательных полей (из security.py: JWT_REQUIRED_CLAIMS)
        assert "sub" in payload  # subject (username)
        assert "exp" in payload  # expiration time
        assert "iat" in payload  # issued at
        assert "type" in payload  # token type ("access")
        assert "jti" in payload  # unique token ID
        
        # Проверяем значения
        assert payload["type"] == "access"
        assert payload["sub"] == valid_credentials["username"]

    def test_login_refresh_token_claims(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
        """A32: Refresh токен содержит обязательные claims"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        payload = jwt.decode(data["refresh_token"], valid_secret_key, algorithms=valid_jwt_algorithm)
        
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert "jti" in payload
        
        assert payload["type"] == "refresh"
        assert payload["sub"] == valid_credentials["username"]

    """Тесты JWT-токенов"""
    def test_login_token_expiration(self, client, valid_credentials, valid_expires_in, valid_secret_key, valid_jwt_algorithm):
        """A33: Access токен имеет правильное время жизни"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        payload = jwt.decode(data["access_token"], valid_secret_key, algorithms=valid_jwt_algorithm)
        
        # exp - iat должно быть равно expires_in
        assert payload["exp"] - payload["iat"] == valid_expires_in
        
        # expires_in в ответе должен совпадать
        assert data["expires_in"] == valid_expires_in
    
    def test_login_token_unique_jti(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
        """A34: Каждый токен имеет уникальный jti (JWT ID)"""
        
        # Первый вход
        response1 = client.post("/auth/login", json=valid_credentials)
        payload1 = jwt.decode(response1.json()["access_token"], valid_secret_key, algorithms=valid_jwt_algorithm)
        
        # Второй вход
        response2 = client.post("/auth/login", json=valid_credentials)
        payload2 = jwt.decode(response2.json()["access_token"], valid_secret_key, algorithms=valid_jwt_algorithm)
        
        # jti должны быть разными
        assert payload1["jti"] != payload2["jti"]
