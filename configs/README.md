# Конфигурационные файлы

1) `proxy.conf` — nginx-конфиг для проксирования запросов. `/api/*` идёт на бэкенд, `/` — на фронтенд.
2) `frontend.conf` — nginx-конфиг для фронтенда.
3) `backend.env` — не секретные параметры бэкенда. Сейчас используются:
```env
DRONE_CORS_ORIGINS=http://localhost,https://localhost,http://127.0.0.1,http://127.0.0.1:5173,http://localhost:5173
ELASTIC_URL=http://elastic:9200
```
4) `elastic.env` — переменные окружения для Elasticsearch.
5) `init-elastic.yaml` — конфиг для init-контейнера Elasticsearch. Поддерживает поле:
`elastic_url: http://elastic:9200`
