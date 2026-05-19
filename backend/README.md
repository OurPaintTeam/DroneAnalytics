# Backend

Бэкенд отвечает за API, логи и авторизацию.

## Авторизация

Схема хранения токенов:
- `access_token` — в `localStorage` на фронтенде;
- `refresh_token` — в `HttpOnly` cookie.

Эндпоинты:
- `POST /auth/login` — выдаёт access token и ставит refresh cookie;
- `POST /auth/refresh` — обновляет access token по refresh cookie;
- `POST /auth/logout` — очищает refresh cookie.

## Секреты

Бэкенд читает только `/run/secrets/backend.yaml`.
Файл должен содержать как минимум:
- `secret_key`
- `api_keys`
- `redis.username`
- `redis.password`
- `users`
- `accounts`

Пример структуры — в `secrets/README.md`.

`accounts` задаёт статическое стартовое состояние для `GET /accounts`: роли, привязанные сервисы, `balance` и `reserved`.
Поле `updated_at` хранится в Redis и обновляется backend-ом при успешной записи event/safety логов.

## Запуск

- порт 8080
- .env - переменные окружения
