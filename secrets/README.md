# Секреты - чувствительные данные
## proxy.crt
Сертификат для https, монтируется к proxy
## proxy.key
Ключ для https, монтируется к  proxy
## backend.yaml
Пароли и ключи для backend. Формат:  
```yaml
secret_key: "replace-with-a-long-random-string"

api_keys:
  - "change-me-api-key"
  - "change-me-api-key-2"

users:
  user: "$2b$12$bH1DGAjHXwgqNmFuYiiALeYK9dOtst43lB/HwUM0qhte2IeNGw4O."
  alice:
    password_hash: "$2b$12$..."
```
`password_hash` должен быть результатом `python tools/make_hash.py <password>`.  

`users` можно задавать и в короткой форме, и в виде объекта с `password_hash`.
## Тестовый запуск
Для того, чтобы легко и просто, для локального тестирования, сконфигурировать секреты, можно запустить команду из корня проекта:
```shell
make secrets
```