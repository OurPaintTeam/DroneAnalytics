"""
Тесты для эндпоинтов авторизации (POST /auth/refresh)
"""
import jwt
import time

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

    def test_refresh_invalid_signature(self, client, valid_jwt_algorithm, valid_expires_in):
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
            algorithm=valid_jwt_algorithm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": fake_token
        })
        assert response.status_code == 401

    def test_refresh_expired_token(self, client, valid_credentials, valid_jwt_algorithm, valid_secret_key):
        """R13: Просроченный refresh_token -> 401"""
        # Получаем валидный токен
        login = client.post("/auth/login", json=valid_credentials)
        refresh_token = login.json()["refresh_token"]

        # Декодируем и модифицируем время истечения
        payload = jwt.decode(refresh_token, valid_secret_key, algorithms=valid_jwt_algorithm)
        payload["exp"] = int(time.time()) - 100  # В прошлом

        expired_token = jwt.encode(payload, valid_secret_key, algorithm=valid_jwt_algorithm)

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
    
    def test_refresh_missing_jti_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm, valid_expires_in):
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
            algorithm=valid_jwt_algorithm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_sub_claim(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algorithm):
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
            algorithm=valid_jwt_algorithm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_exp_claim(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
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
            algorithm=valid_jwt_algorithm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_iat_claim(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algorithm):
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
            algorithm=valid_jwt_algorithm
        )

        response = client.post("/auth/refresh", json={
            "refresh_token": invalid_token
        })
        assert response.status_code == 401

    def test_refresh_missing_type_claim(self, client, valid_credentials, valid_expires_in, valid_secret_key, valid_jwt_algorithm):
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
            algorithm=valid_jwt_algorithm
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
    
    def test_refresh_empty_subject(self, client, valid_credentials, valid_secret_key, valid_expires_in, valid_jwt_algorithm):
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
            algorithm=valid_jwt_algorithm
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

    def test_refresh_access_token_is_valid_jwt(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
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
            algorithms=valid_jwt_algorithm
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

    def test_refresh_refresh_token_is_valid_jwt(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm):
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
            algorithms=valid_jwt_algorithm
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
