# DroneAnalytics
service of analytics and informaton panels for discipline "Cyberimmune Systems Software Engineering"
## Запуск
### Переменные окружения
Примерно каждый микросервис требует переменные окружения в своей папке. Их содержимое( я бы вообще не включал эту информацию, но нужны сквозные тесты):  
backend:  
```
DRONE_CORS_ORIGINS=*
DRONE_API_KEY=change-me
```  
elastic:
```
discovery.type=single-node
xpack.security.enabled=false
ES_JAVA_OPTS=-Xms512m -Xmx512m
```
frontend:
```
VITE_BACKEND_URL=https://localhost/api
```
init-elastic:
```
ELASTIC_URL=http://elastic:9200
```
### https
Для прокси нужны сертификаты. Они должны храниться в папке proxy/certs.
### Запуск
Система позволяет запускаться через docker-compose из под корневой директории.
```shell
docker-compose up --build
```
### Ожидание
Это важно. ElasticSearch и, соответсвенно, его инит контейнер стартуют не мнгновенно. Не надо паниковать,
они стартуют примерно через минуту. Система это учитывает - прокси стартует только после завершения инит контейнера.