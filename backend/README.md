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
- `users`

Пример структуры — в `secrets/README.md`.

## Запуск

- порт: `8080`
- общие параметры для бэкенда: `configs/backend.env`
