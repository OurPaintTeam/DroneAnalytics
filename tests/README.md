# Описание
Хранятся тесты для кода, в отдельных папках для отдельных частей кода.

По умолчанию запуск тестов имеет следующие настройки:
- `-vv` + `-ra` + `--tb=short` для детального отчёта по тестам;

Настройки меняются в pytest.ini

# Запуск
Надо из корня проекта запустить 
```shell
make tests
```
Если у вас не установленно окружение, читайте [ README ]( ../README.md )

## Покрытие backend
После `make tests` backend останавливается автоматически, файл покрытия сразу сохраняется в `coverage_data`, и в консоль печатается `coverage report`.

### Как именно считается coverage для `backend`
Ниже — полный путь, чтобы было понятно, кто и в какой момент пишет данные:

1. `make tests` запускает `docker compose --profile tests up -d --build` с переменной `COVERAGE_MODE=true` (по умолчанию она false).
2. Контейнер `backend` получает `COVERAGE_MODE=true` через `docker-compose.yaml` и стартует через `backend/docker-entrypoint.sh` в режиме:
   - `coverage run --parallel-mode`
   - `--source=/app/app` (учитывается только код backend-приложения, его покрытие смотрится)
   - `--data-file=/app/coverage_data/.coverage` (базовый путь для файлов покрытия, куда их сохранять)
3. Тесты выполняются в отдельном контейнере `tests` и ходят в backend по сети. Из-за раздельных контейнеров покрытие считает именно процесс backend, а не pytest в контейнере tests.
4. Во время жизни backend coverage держит данные в процессе и в служебных файлах. Финальная запись полного набора строк/веток происходит при корректной остановке backend-процесса. Поэтому после завершения тестов в `Makefile` выполняется `docker compose stop backend` — это ключевой шаг, который принудительно завершает backend и «сбрасывает» итоговые `.coverage.*` файлы в `./coverage_data` (volume, примонтированный в `/app/coverage_data`).
6. После этого отдельной командой запускается `docker compose run --rm --no-deps tests ... coverage combine ... && coverage report ...`:
   - `coverage combine` объединяет все `.coverage.*` (если backend перезапускался/создал несколько shard-файлов),
   - `coverage report` печатает таблицу покрытия в консоль.

### Где физически лежат файлы покрытия
- На хосте: `./coverage_data/.coverage*`
- Внутри контейнеров backend/tests: `/app/coverage_data/.coverage*`

Это один и тот же набор файлов через bind-mount из `docker-compose.yaml`.

### Типичные сценарии
- **Обычный запуск:** `make tests` — тесты + остановка backend + печать отчёта.
- **Пересобрать отчёт вручную из уже собранных файлов:** см. команду ниже.
- **Если данных нет:** проверьте, что backend действительно запускался с `COVERAGE_MODE=true` и был остановлен после тестов.

Если нужно построить отчёт вручную из уже собранных файлов (без локальной установки `coverage`):
```shell
docker compose run --rm --no-deps tests sh -c "coverage combine --keep /app/coverage_data/.coverage.* && COVERAGE_RCFILE=/dev/null coverage report --fail-under=0 --show-missing"
```