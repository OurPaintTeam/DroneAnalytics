# Описание
Единственная точка входа в систему. Используется nginx - как прокси. Имеет несколько типов проксирования:
 - http -> https
 - https://infopanel.csse.ru/some/path/ -> frontend/some/path/
 - https://infopanel.csse.ru/api/some/path/ -> backend/some/path/
## Запуск
 - использует сертификаты из папки certs
 - порты 80 и 443