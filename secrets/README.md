# Секреты

В этой папке лежат только чувствительные данные.


Минимальный формат:

```yaml
secret_key: "replace-with-a-long-random-string"

api_keys:
  - "replace-with-api-key-1"
  - "replace-with-api-key-2"

users:
  alice:
    password_hash: "$2b$12$..."
  bob: "$2b$12$..."
```

`password_hash` должен быть результатом `python tools/make_hash.py <password>`.

`users` можно задавать и в короткой форме, и в виде объекта с `password_hash`.

# Секреты - чувствительные данные
 - `proxy.crt` и `proxy.key` - сертификаты для https
 - `backend.yaml` - пароли и ключи бэкенда. Подробная структура будет описана позже  

Для того, чтобы легко и просто, для локального тестирования, сконфигурировать секреты, можно запустить команду из корня проекта:
```shell
make secrets
```