"""
Тесты для эндпоинтов авторизации (POST /auth/logout)
"""
import jwt
import time

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

    def test_logout_expired_access_token(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm, valid_expires_in):
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
            algorithm=valid_jwt_algorithm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    def test_logout_expired_refresh_token(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm, valid_ref_in):
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
            algorithm=valid_jwt_algorithm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": expired_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    def test_logout_mismatched_tokens(self, client, valid_credentials, valid_secret_key, valid_jwt_algorithm, valid_expires_in):
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
            algorithm=valid_jwt_algorithm
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

    def test_logout_access_token_without_sub_claim(self, client, valid_credentials, valid_expires_in, valid_secret_key, valid_jwt_algorithm):
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
            "exp": current_time + valid_expires_in,
            "jti": "no_sub_jti_22222"
            # Нет поля 'sub'!
        }
        token_without_sub = jwt.encode(
            payload_without_sub,
            valid_secret_key,
            algorithm=valid_jwt_algorithm
        )
        
        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {token_without_sub}"}
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["message"]

    def test_logout_refresh_token_without_sub_claim(self, client, valid_credentials, valid_ref_in, valid_secret_key, valid_jwt_algorithm):
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
            "exp": current_time + valid_ref_in,
            "jti": "no_sub_refresh_jti_33333"
            # Нет поля 'sub'!
        }
        token_without_sub = jwt.encode(
            payload_without_sub,
            valid_secret_key,
            algorithm=valid_jwt_algorithm
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