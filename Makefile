all: prod

prod:
	docker compose --profile app up -d --build

# It's just a example of certs. It's not for production. IT'S FOR LOCAL TESTS
secrets:
	openssl req -x509 -nodes -days 365 \
		-newkey rsa:2048 \
		-keyout secrets/proxy.key \
		-out secrets/proxy.crt \
		-subj "/CN=localhost"
	touch ./secrets/backend.yaml
	printf "secret_key: \"replace-with-a-long-random-string\"\napi_keys:\n  - \"change-me-api-key\"\nredis:\n  username: \"app\"\n  password: \"soStrongApp\"\nusers:\n  user: \"" > ./secrets/backend.yaml
	(python3 tools/make_hash.py password) >> ./secrets/backend.yaml
	printf "\"\naccounts:\n  - account_id: aggregator\n    name: \"Агрегатор\"\n    services: [\"aggregator\", \"infopanel\"]\n    balance: 100\n    reserved: 0\n  - account_id: operator\n    name: \"Эксплуатант\"\n    services: [\"operator\", \"GCS\", \"dronePort\"]\n    balance: 100\n    reserved: 0\n  - account_id: insurance\n    name: \"Страховая компания\"\n    services: [\"insurance\"]\n    balance: 100\n    reserved: 0\n  - account_id: developer\n    name: \"Разработчик\"\n    services: [\"delivery\", \"queen\", \"inspector\", \"agriculture\", \"SITL\", \"Gazebo\"]\n    balance: 100\n    reserved: 0\n  - account_id: regulator\n    name: \"Регулятор\"\n    services: [\"regulator\", \"registry\"]\n    balance: 100\n    reserved: 0\n  - account_id: orat_bas\n    name: \"ОрВД БАС\"\n    services: [\"OrAT_drones\"]\n    balance: 100\n    reserved: 0\n  - account_id: customer\n    name: \"Заказчик\"\n    services: []\n    balance: 100\n    reserved: 0\n" >> ./secrets/backend.yaml
	printf "user root on >soStrongRoot allcommands allkeys allchannels \nuser app on >soStrongApp resetchannels -@all +@read +@write +@string +@hash +@list +@set +@sortedset +@stream +@fast +@transaction +@connection ~*\nuser default off nopass -@all" > ./secrets/redis-sec.acl

local: secrets prod

clean:
	docker compose down
	docker rm tests

healthcheck: prod clean

.PHONY: tests secrets

tests:
	docker compose --profile tests up -d --build
	docker logs -f tests
	docker compose stop backend-coverage
	docker compose run --rm --no-deps tests sh -c "if ls /app/coverage_data/.coverage.* 1>/dev/null 2>&1; then coverage combine --keep /app/coverage_data/.coverage.* 2>/dev/null || true; COVERAGE_RCFILE=/dev/null coverage report --fail-under=0 --show-missing; else echo 'No coverage data found in /app/coverage_data/. Run make clean and check backend shutdown logs.'; fi"

unit-tests:

watch:
	docker compose watch
