"""
Тесты для эндпоинтов авторизации (POST /auth/login, /auth/refresh, /auth/logout)
"""
import jwt
import time
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
        
        assert response.status_code == 200
        assert "access_token" in response.json()

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
        
        # FastAPI может вернуть 400
        assert response.status_code in [400]

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
    
    def test_login_access_token_claims(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """A31: Access токен содержит обязательные claims"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        # Декодируем токен (без проверки подписи — только структура)
        payload = jwt.decode(data["access_token"], valid_secret_key, algorithms=valid_jwt_algoritm)
        
        # Проверяем наличие обязательных полей (из security.py: JWT_REQUIRED_CLAIMS)
        assert "sub" in payload  # subject (username)
        assert "exp" in payload  # expiration time
        assert "iat" in payload  # issued at
        assert "type" in payload  # token type ("access")
        assert "jti" in payload  # unique token ID
        
        # Проверяем значения
        assert payload["type"] == "access"
        assert payload["sub"] == valid_credentials["username"]

    def test_login_refresh_token_claims(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """A32: Refresh токен содержит обязательные claims"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        payload = jwt.decode(data["refresh_token"], valid_secret_key, algorithms=valid_jwt_algoritm)
        
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert "jti" in payload
        
        assert payload["type"] == "refresh"
        assert payload["sub"] == valid_credentials["username"]

    """Тесты JWT-токенов"""
    def test_login_token_expiration(self, client, valid_credentials, valid_expires_in, valid_secret_key, valid_jwt_algoritm):
        """A33: Access токен имеет правильное время жизни"""
        
        response = client.post("/auth/login", json=valid_credentials)
        data = response.json()
        
        payload = jwt.decode(data["access_token"], valid_secret_key, algorithms=valid_jwt_algoritm)
        
        # exp - iat должно быть равно expires_in
        assert payload["exp"] - payload["iat"] == valid_expires_in
        
        # expires_in в ответе должен совпадать
        assert data["expires_in"] == valid_expires_in
    
    def test_login_token_unique_jti(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """A34: Каждый токен имеет уникальный jti (JWT ID)"""
        
        # Первый вход
        response1 = client.post("/auth/login", json=valid_credentials)
        payload1 = jwt.decode(response1.json()["access_token"], valid_secret_key, algorithms=valid_jwt_algoritm)
        
        # Второй вход
        response2 = client.post("/auth/login", json=valid_credentials)
        payload2 = jwt.decode(response2.json()["access_token"], valid_secret_key, algorithms=valid_jwt_algoritm)
        
        # jti должны быть разными
        assert payload1["jti"] != payload2["jti"]

class TestAuthRefresh:
    """Тесты для POST /auth/refresh"""

    # ==================== ПОЗИТИВНЫЕ ТЕСТЫ ====================

    def test_refresh_success(self, client, valid_credentials, valid_expires_in):
        """R1: Успешное обновление токена"""
        # Сначала логинимся, чтобы получить refresh_token
        login_response = client.post("/auth/login", json=valid_credentials)
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Обновляем токен
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == valid_expires_in  # Из config.py

    def test_refresh_token_short(self, client):
        """R2: refresh_token ровно 16 символов -> 200 (валидно) или 401 (неверная подпись)"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "x" * 16 
        })
        assert response.status_code in [200, 401]

    def test_refresh_token_long(self, client):
        """R3: refresh_token 1024 символов -> 200 или 401"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "x" * 1024 
        })
        assert response.status_code in [200, 401]

    def test_refresh_chain(self, client, valid_credentials):
        """R4: Многократное обновление (цепочка токенов)"""
        # Логинимся
        login = client.post("/auth/login", json=valid_credentials)
        token = login.json()["refresh_token"]

        # Обновляем 3 раза
        for i in range(3):
            response = client.post("/auth/refresh", json={
                "refresh_token": token
            })
            assert response.status_code == 200
            token = response.json()["refresh_token"]  # Берём новый refresh_token

    # ==================== ТЕСТЫ ВАЛИДАЦИИ (PYDANTIC) ====================

    def test_refresh_empty_token(self, client):
        """R5: Пустой refresh_token -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": ""
        })
        assert response.status_code == 400

    def test_refresh_token_too_short(self, client):
        """R6: refresh_token короче 16 символов -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "x" * 15  # 15 символов, минимум 16
        })
        assert response.status_code == 400

    def test_refresh_token_too_long(self, client):
        """R7: refresh_token длиннее 1024 символов -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "x" * 1025  # 1025 символов, максимум 1024
        })
        assert response.status_code == 400

    def test_refresh_missing_field(self, client):
        """R8: Отсутствует поле refresh_token -> 400"""
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 400

    def test_refresh_extra_field(self, client, valid_credentials):
        """R9: Лишнее поле в JSON -> 400 (StrictModel)"""
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token,
            "extra_field": "should_fail"
        })
        assert response.status_code == 400

    def test_refresh_wrong_type(self, client):
        """R10: Неверный тип данных (число вместо строки) -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": 12345  # Должна быть строка
        })
        assert response.status_code == 400

    def test_refresh_null_value(self, client):
        """R11: null вместо строки -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": None
        })
        assert response.status_code == 400

    # ==================== ТЕСТЫ JWT-ВАЛИДАЦИИ ====================

    def test_refresh_invalid_signature(self, client, valid_jwt_algoritm, valid_expires_in):
        """R12: Токен с неверной подписью -> 401"""
        # Создаём токен с неправильной подписью
        fake_token = jwt.encode(
            payload={
                "sub": "user",
                "type": "refresh",
                "exp": int(time.time()),
                "iat": int(time.time())+valid_expires_in,
                "jti": "fake_jti"
            },
            key="wrong_secret_key",  # Неправильный ключ
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": fake_token
        })
        assert response.status_code == 401

    def test_refresh_expired_token(self, client, valid_credentials, valid_jwt_algoritm, valid_secret_key):
        """R13: Просроченный refresh_token -> 401"""
        # Получаем валидный токен
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        # Декодируем и модифицируем время истечения
        payload = jwt.decode(refresh_token, valid_secret_key, algorithms=valid_jwt_algoritm)
        payload["exp"] = int(time.time()) - 100  # В прошлом

        expired_token = jwt.encode(payload, valid_secret_key, algorithm=valid_jwt_algoritm)

        response = client.post("/auth/refresh", json={
            "refresh_token": expired_token
        })
        assert response.status_code == 401

    def test_refresh_access_token_instead(self, client, valid_credentials):
        """R14: Передан access_token вместо refresh -> 401"""
        # Логинимся
        login = client.post("/auth/login", json=valid_credentials)
        access_token = login.json()["access_token"]

        # Пытаемся использовать access_token как refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": access_token
        })
        assert response.status_code == 401
    
    def test_refresh_missing_jti_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm, valid_expires_in):
        """R15: Токен без claim 'jti' -> 401"""
        
        # Создаём токен без обязательного claim 'jti'
        invalid_token = jwt.encode(
            payload={
                "sub": valid_credentials["username"],
                "type": "refresh",
                "exp": int(time.time()),
                "iat": int(time.time())+valid_expires_in,
                # Нет 'jti'!
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_sub_claim(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algoritm):
        """R16: Токен без claim 'sub' -> 401"""
        
        invalid_token = jwt.encode(
            payload={
                # Нет 'sub'!
                "type": "refresh",
                "exp": int(time.time()),
                "iat": int(time.time())+valid_expires_in,
                "jti": "test_jti"
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_exp_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """R17: Токен без claim 'exp' -> 401"""
        
        invalid_token = jwt.encode(
            payload={
                "sub": valid_credentials["username"],
                "type": "refresh",
                # Нет 'exp'!
                "iat": int(time.time()),
                "jti": "test_jti"
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_iat_claim(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algoritm):
        """R18: Токен без claim 'iat' -> 401"""
        
        invalid_token = jwt.encode(
            payload={
                "sub": valid_credentials["username"],
                "type": "refresh",
                "exp": int(time.time()) + valid_expires_in,
                # Нет 'iat'!
                "jti": "test_jti"
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_type_claim(self, client, valid_credentials, valid_expires_in, valid_secret_key, valid_jwt_algoritm):
        """R19: Токен без claim 'type' -> 401"""
        
        invalid_token = jwt.encode(
            payload={
                "sub": valid_credentials["username"],
                # Нет 'type'!
                "exp": int(time.time()),
                "iat": int(time.time())+valid_expires_in,
                "jti": "test_jti"
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401


    def test_refresh_not_jwt_string(self, client):
        """R20: Не JWT-строка -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "not-a-jwt-token"
        })
        assert response.status_code in [400, 401]

    def test_refresh_malformed_jwt(self, client):
        """R21: Повреждённая структура JWT (не 3 части) -> 400"""
        response = client.post("/auth/refresh", json={
            "refresh_token": "only.two"  # Должно быть 3 части
        })
        assert response.status_code == 400
    
    def test_refresh_empty_subject(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algoritm):
        """R22: Токен с пустым subject (sub="") -> 401"""
        
        invalid_token = jwt.encode(
            payload={
                "sub": "",  # Пустой subject
                "type": "refresh",
                "exp": int(time.time()),
                "iat": int(time.time())+valid_expires_in,
                "jti": "test_jti"
            },
            key=valid_secret_key,
            algorithm=valid_jwt_algoritm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401
    # ==================== ТЕСТЫ ФОРМАТА ЗАПРОСА/ОТВЕТА ====================

    def test_refresh_response_structure(self, client, valid_credentials):
        """R23: Проверка структуры ответа"""
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        data = response.json()
        # Проверяем все обязательные поля
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data

    def test_refresh_token_type(self, client, valid_credentials):
        """R24: Проверка token_type == "Bearer" """
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.json()["token_type"] == "Bearer"

    def test_refresh_expires_in(self, client, valid_credentials, valid_expires_in):
        """R25: Проверка expires_in == valid_expires_in"""
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.json()["expires_in"] == valid_expires_in

    def test_refresh_correct_content_type(self, client, valid_credentials):
        """R26: Правильный Content-Type: application/json -> 200"""
        # Сначала получаем валидный refresh_token
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        # Отправляем с правильным заголовком
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_wrong_method(self, client, valid_credentials):
        """R27 GET вместо POST -> 405"""
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.get("/auth/refresh", params={
            "refresh_token": refresh_token
        })
        assert response.status_code == 405

    def test_refresh_wrong_content_type(self, client, valid_credentials):
        """R28: Неправильный Content-Type -> 400"""
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        response = client.post(
            "/auth/refresh",
            content=str({"refresh_token": refresh_token}),  # Не JSON
            headers={"Content-Type": "text/plain"}
        )
        # FastAPI может вернуть 400
        assert response.status_code in [400, 422]
    
    def test_refresh_tokens_are_unique(self, client, valid_credentials):
        """R29: каждый refresh выдаёт новые уникальные токены"""
        # Логинимся — получаем первую пару токенов
        login = client.post("/auth/login", json=valid_credentials)
        first_access = login.json()["access_token"]
        first_refresh = login.json()["refresh_token"]

        # Делаем refresh — получаем вторую пару
        response1 = client.post("/auth/refresh", json={
            "refresh_token": first_refresh
        })
        second_access = response1.json()["access_token"]
        second_refresh = response1.json()["refresh_token"]

        # Токены должны быть разными
        assert first_access != second_access, "access_token должен измениться"
        assert first_refresh != second_refresh, "refresh_token должен измениться"

        # Делаем ещё один refresh — третья пара
        response2 = client.post("/auth/refresh", json={
            "refresh_token": second_refresh
        })
        third_access = response2.json()["access_token"]
        third_refresh = response2.json()["refresh_token"]

        # Все токены должны быть уникальны
        assert second_access != third_access
        assert second_refresh != third_refresh
        assert first_access != third_access  # Даже через один шаг

    def test_refresh_access_token_is_valid_jwt(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """R30: access_token в ответе — валидный JWT с правильными claim'ами"""
        
        # Логинимся и получаем refresh_token
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        # Делаем refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # === Проверка access_token ===
        access_token = data["access_token"]
        
        # 1. Базовая проверка: не пустой, строка, формат JWT
        assert isinstance(access_token, str)
        assert len(access_token) > 0
        assert access_token.count(".") == 2, "access_token должен иметь формат JWT (3 части)"
        
        # 2. Декодируем и проверяем claim'ы (без проверки подписи — она тестируется отдельно)
        decoded = jwt.decode(
            access_token,
            valid_secret_key,
            algorithms=valid_jwt_algoritm
        )
        
        # 3. Проверяем обязательные поля
        assert "sub" in decoded, "access_token должен содержать claim 'sub'"
        assert "type" in decoded, "access_token должен содержать claim 'type'"
        assert "exp" in decoded, "access_token должен содержать claim 'exp'"
        assert "iat" in decoded, "access_token должен содержать claim 'iat'"
        assert "jti" in decoded, "access_token должен содержать claim 'jti'"
        
        # 4. Проверяем значения
        assert decoded["type"] == "access", "claim 'type' должен быть 'access'"
        assert isinstance(decoded["sub"], str) and len(decoded["sub"]) > 0, "sub должен быть непустой строкой"
        assert isinstance(decoded["exp"], int) and decoded["exp"] > decoded["iat"], "exp должен быть больше iat"

    def test_refresh_refresh_token_is_valid_jwt(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """R31: refresh_token в ответе — валидный JWT с правильными claim'ами"""
        
        # Логинимся и получаем refresh_token
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        # Делаем refresh
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # === Проверка refresh_token ===
        new_refresh_token = data["refresh_token"]
        
        # 1. Базовая проверка: не пустой, строка, формат JWT
        assert isinstance(new_refresh_token, str)
        assert len(new_refresh_token) > 0
        assert new_refresh_token.count(".") == 2, "refresh_token должен иметь формат JWT (3 части)"
        
        # 2. Декодируем и проверяем claim'ы (без проверки подписи — она тестируется отдельно)
        decoded = jwt.decode(
            new_refresh_token,
            valid_secret_key,
            algorithms=valid_jwt_algoritm
        )
        
        # 3. Проверяем обязательные поля
        assert "sub" in decoded, "refresh_token должен содержать claim 'sub'"
        assert "type" in decoded, "refresh_token должен содержать claim 'type'"
        assert "exp" in decoded, "refresh_token должен содержать claim 'exp'"
        assert "iat" in decoded, "refresh_token должен содержать claim 'iat'"
        assert "jti" in decoded, "refresh_token должен содержать claim 'jti'"
        
        # 4. Проверяем значения
        assert decoded["type"] == "refresh", "claim 'type' должен быть 'refresh'"
        assert isinstance(decoded["sub"], str) and len(decoded["sub"]) > 0, "sub должен быть непустой строкой"
        assert isinstance(decoded["exp"], int) and decoded["exp"] > decoded["iat"], "exp должен быть больше iat"


class TestAuthLogout:
    """Позитивные тесты — успешный выход"""

    def test_logout_success(self, client, valid_credentials):
        """
        L1: Успешный выход с валидными токенами
        
        Шаги:
        1. Логинимся и получаем пару токенов
        2. Отправляем logout с refresh_token + Bearer access_token
        3. Проверяем ответ 200 OK
        """
        # Шаг 1: Получаем токены
        login_response = client.post("/auth/login", json=valid_credentials)
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Шаг 2: Делаем logout
        logout_response = client.post(
            "/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        # Шаг 3: Проверяем ответ
        assert logout_response.status_code == 200
        assert logout_response.json() == {"status": "ok"}

    """Тесты валидации Pydantic-модели (RefreshTokenRequest)"""

    def test_logout_empty_refresh_token(self, client, valid_credentials):
        """L2: Пустой refresh_token -> 400"""
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": ""},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400

    def test_logout_refresh_token_too_short(self, client, valid_credentials):
        """L3: refresh_token < 16 символов -> 400"""
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "short"},  # 5 символов, минимум 16
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400

    def test_logout_refresh_token_too_long(self, client, valid_credentials):
        """L4: refresh_token > 1024 символов -> 400"""
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "x" * 1025},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400

    def test_logout_missing_refresh_token(self, client, valid_credentials):
        """L5: Отсутствует поле refresh_token -> 400"""
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            json={},  # Нет refresh_token
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400

    def test_logout_extra_field_forbidden(self, client, valid_credentials):
        """L6: Лишнее поле в теле -> 400 (StrictModel)"""
        login_response = client.post("/auth/login", json=valid_credentials)
        tokens = login_response.json()
        
        response = client.post(
            "/auth/logout",
            json={
                "refresh_token": tokens["refresh_token"],
                "extra_field": "should_fail"  # StrictModel запрещает
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        assert response.status_code == 400

    """Тесты авторизации (заголовки)"""

    def test_logout_no_authorization_header(self, client, valid_credentials):
        """L7: Нет заголовка Authorization -> 401"""
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        # Нет заголовка Authorization!
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["message"]

    def test_logout_wrong_auth_scheme(self, client, valid_credentials):
        """L8: Неверный формат заголовка (Basic вместо Bearer) -> 401"""
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": "Basic dXNlcjpwYXNz"}  # Base64
        )
        
        assert response.status_code == 401

    def test_logout_empty_bearer_token(self, client, valid_credentials):
        """L9: Пустой Bearer токен -> 401"""
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": "Bearer "}  # Пусто после Bearer
        )
        
        assert response.status_code == 401

    def test_logout_invalid_jwt_format(self, client, valid_credentials):
        """L10: Не JWT-строка в Bearer -> 401"""
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": "Bearer not-a-jwt-token"}
        )
        
        assert response.status_code == 401

    """Тесты валидности и соответствия токенов"""

    def test_logout_expired_access_token(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm, valid_expires_in):
        """
        L11: Просроченный access_token -> 401
        
        Создаём токен с exp в прошлом, используя SECRET_KEY из config.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        # Создаём просроченный access_token вручную
        past_time = int(time.time()) - 3600  # 1 час назад
        expired_payload = {
            "sub": valid_credentials["username"],
            "type": "access",
            "iat": past_time - valid_expires_in,
            "exp": past_time,  # Истёк 1 час назад
            "jti": "expired_jti_12345"
        }
        expired_token = jwt.encode(
            expired_payload,
            valid_secret_key,
            algorithm=valid_jwt_algoritm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    def test_logout_expired_refresh_token(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm, valid_ref_in):
        """
        L12: Просроченный refresh_token -> 401
        
        Создаём refresh_token с exp в прошлом.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        # Создаём просроченный refresh_token вручную
        past_time = int(time.time()) - 86400  # 1 день назад
        expired_payload = {
            "sub": valid_credentials["username"],
            "type": "refresh",
            "iat": past_time - valid_ref_in,
            "exp": past_time,  # Истёк 1 день назад
            "jti": "expired_refresh_jti_67890"
        }
        expired_token = jwt.encode(
            expired_payload,
            valid_secret_key,
            algorithm=valid_jwt_algoritm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": expired_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    def test_logout_mismatched_tokens(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm, valid_expires_in):
        """
        L13: Токены от разных пользователей -> 401
        
        Создаём второй токен от другого пользователя и смешиваем с первым.
        """
        # Получаем токены для основного пользователя
        login_response = client.post("/auth/login", json=valid_credentials)
        tokens_user1 = login_response.json()
        
        # Создаём access_token от ДРУГОГО пользователя (используем тот же SECRET_KEY)
        current_time = int(time.time())
        other_user_payload = {
            "sub": "other_user",  # Другой пользователь!
            "type": "access",
            "iat": current_time,
            "exp": current_time + valid_expires_in,
            "jti": "other_user_jti_11111"
        }
        other_user_token = jwt.encode(
            other_user_payload,
            valid_secret_key,
            algorithm=valid_jwt_algoritm
        )
        
        # Пытаемся сделать logout: refresh от user1, access от other_user
        response = client.post(
            "/auth/logout",
            json={"refresh_token": tokens_user1["refresh_token"]},
            headers={"Authorization": f"Bearer {other_user_token}"}
        )
        
        assert response.status_code == 401
        assert "does not belong to current user" in response.json()["message"]

    def test_logout_invalid_access_token_signature(self, client, valid_credentials):
        """
        L14: Неверная подпись access_token -> 401
        
        Берём валидный токен и портим подпись (последняя часть JWT).
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        valid_access = login_response.json()["access_token"]
        
        # Разбиваем JWT на части и портим подпись
        parts = valid_access.split(".")
        tampered_access = f"{parts[0]}.{parts[1]}.tampered_signature_here"
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {tampered_access}"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["message"]

    def test_logout_invalid_refresh_token_signature(self, client, valid_credentials):
        """
        L15: Неверная подпись refresh_token -> 401
        
        Берём валидный refresh_token и портим подпись.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        valid_refresh = login_response.json()["refresh_token"]
        
        # Разбиваем JWT на части и портим подпись
        parts = valid_refresh.split(".")
        tampered_refresh = f"{parts[0]}.{parts[1]}.tampered_signature_here"
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": tampered_refresh},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["message"]

    def test_logout_access_token_without_sub_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """
        L16: access_token без claim 'sub' -> 401
        
        Создаём токен без обязательного поля 'sub'.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        # Создаём токен БЕЗ поля 'sub'
        current_time = int(time.time())
        payload_without_sub = {
            "type": "access",
            "iat": current_time,
            "exp": current_time + 900,
            "jti": "no_sub_jti_22222"
            # Нет поля 'sub'!
        }
        token_without_sub = jwt.encode(
            payload_without_sub,
            valid_secret_key,
            algorithm=valid_jwt_algoritm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {token_without_sub}"}
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["message"]

    def test_logout_refresh_token_without_sub_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algoritm):
        """
        L17: refresh_token без claim 'sub' -> 401
        
        Создаём refresh_token без обязательного поля 'sub'.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        # Создаём токен БЕЗ поля 'sub'
        current_time = int(time.time())
        payload_without_sub = {
            "type": "refresh",
            "iat": current_time,
            "exp": current_time + 604800,
            "jti": "no_sub_refresh_jti_33333"
            # Нет поля 'sub'!
        }
        token_without_sub = jwt.encode(
            payload_without_sub,
            valid_secret_key,
            algorithm=valid_jwt_algoritm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": token_without_sub},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["message"]

    def test_logout_wrong_token_type(self, client, valid_credentials):
        """
        L18: Неверный тип токена (access вместо refresh) -> 401
        
        Передаём access_token в поле refresh_token.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        tokens = login_response.json()
        
        # Передаём access_token вместо refresh_token
        response = client.post(
            "/auth/logout",
            json={"refresh_token": tokens["access_token"]},  # Неверный тип!
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["message"]
    
    def test_logout_refresh_token_in_authorization_header(self, client, valid_credentials):
        """
        L19: В заголовке Authorization передан refresh_token вместо access_token -> 401
        
        Проверяем, что система различает типы токенов и не принимает
        refresh_token в заголовке Authorization.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        tokens = login_response.json()
        
        # Передаём refresh_token в заголовке вместо access_token
        response = client.post(
            "/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"}  # Неверный тип токена!
        )
        
        assert response.status_code == 401
        # Сервер должен отклонить, потому что это refresh_token, а не access_token
        assert "Invalid" in response.json()["message"] or "token" in response.json()["message"].lower()

    def test_logout_authorization_header_only_colon(self, client, valid_credentials):
        """
        L20: Заголовок Authorization с пустым значением -> 401
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": ""}  # Пустой заголовок
        )
        
        assert response.status_code == 401

    def test_logout_wrong_content_type(self, client, valid_credentials):
        """
        L21: Неверный Content-Type (text/plain вместо application/json) -> 400
        
        Проверяем, что сервер отвергает запросы с неверным Content-Type.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        tokens = login_response.json()
        
        response = client.post(
            "/auth/logout",
            content='{"refresh_token": "' + tokens["refresh_token"] + '"}',  # Передаём как bytes
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "text/plain"  # Неверный тип!
            }
        )
        
        # FastAPI может вернуть 400
        assert response.status_code in [400, 422]

    def test_logout_malformed_json(self, client, valid_credentials):
        """
        L22: Malformed JSON в теле запроса -> 400
        
        Проверяем обработку некорректного JSON (синтаксическая ошибка).
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        # Невалидный JSON (нет закрывающей кавычки)
        response = client.post(
            "/auth/logout",
            content='{"refresh_token": "broken',  # Malformed JSON
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 400

    def test_logout_json_array_instead_of_object(self, client, valid_credentials):
        """
        L23: Массив вместо объекта в теле запроса -> 400
        
        Проверяем, что сервер ожидает объект, а не массив.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            json=[{"refresh_token": "some_token"}],  # Массив вместо объекта
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400

    def test_logout_empty_body(self, client, valid_credentials):
        """
        L24: Пустое тело запроса -> 400
        
        Проверяем обработку запроса без тела.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            content='',  # Пустое тело
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 400

    def test_logout_null_body(self, client, valid_credentials):
        """
        L25: null вместо объекта в теле запроса -> 400
        
        Проверяем обработку null значения.
        """
        login_response = client.post("/auth/login", json=valid_credentials)
        access_token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/logout",
            content='null',  # null
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400