# DroneAnalytics
service of analytics and informaton panels for discipline "Cyberimmune Systems Software Engineering"
## Быстрый старт
Если не хочешь вникать, то надо просто:
```shell
make local
```
А как закончишь - сделай `make clean`.
## Запуск
### configs
Подробно можно прочитать в [README](configs/README.md)
### secrets
Подробно можно прочитать в [README](secrets/README.md). Дле тестовой генерации можно использовать `make secrets`.
Тогда: апи ключ для журнала - change-me-api-key. Пользователь инфопанели - user. Его пароль - password.
###  Запуск
```shell
docker-compose up --build
```
или
```shell
make
```
### Ожидание
Это важно. ElasticSearch и, соответсвенно, его инит контейнер стартуют не мнгновенно. Не надо паниковать,
они стартуют примерно через минуту. Система это учитывает - прокси стартует только после завершения инит контейнера.