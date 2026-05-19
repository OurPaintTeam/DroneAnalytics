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

redis:
  username: "app"
  password: "soStrongApp"

users:
  user: "$2b$12$bH1DGAjHXwgqNmFuYiiALeYK9dOtst43lB/HwUM0qhte2IeNGw4O."
  alice:
    password_hash: "$2b$12$..."

accounts:
  - account_id: aggregator
    name: "Агрегатор"
    services: ["aggregator", "infopanel"]
    balance: 100
    reserved: 0
  - account_id: operator
    name: "Эксплуатант"
    services: ["operator", "GCS", "dronePort"]
    balance: 100
    reserved: 0
```
`password_hash` должен быть результатом `python tools/make_hash.py <password>`.  

`users` можно задавать и в короткой форме, и в виде объекта с `password_hash`.
`redis.username` и `redis.password` используются только backend-контейнером для подключения к Redis.
`accounts` задаёт статическое начальное состояние витрины аккаунтов их сервисы и стартовые суммы.
`updated_at` backend обновляет его в Redis по мере прихода event/safety логов.
## redis-sec.acl
Конфиг с ACL-политикой Redis. Вот пример:
```acl
user root on >soStrongRoot allcommands allkeys allchannels
user app on >soStrongApp resetchannels -@all +@read +@write +@string +@hash +@list +@set +@sortedset +@stream +@fast +@transaction +@connection ~*
user default off nopass -@all
```
## Тестовый запуск
Для того, чтобы легко и просто, для локального тестирования, сконфигурировать секреты, можно запустить команду из корня проекта:
```shell
make secrets
```