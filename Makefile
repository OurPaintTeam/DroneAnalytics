all: prod

prod:
	docker compose up -d --build

# It's just a example of certs. It's not for production. IT'S FOR LOCAL TESTS
secrets:
	openssl req -x509 -nodes -days 365 \
		-newkey rsa:2048 \
		-keyout secrets/proxy.key \
		-out secrets/proxy.crt \
		-subj "/CN=localhost"
	touch ./secrets/backend.yaml
	printf "secret_key: \"replace-with-a-long-random-string\"\napi_keys: ["change-me-api-key"]\nusers:\n  user: \"" > ./secrets/backend.yaml
	(python3 tools/make_hash.py password) >> ./secrets/backend.yaml
	echo "\"" >> ./secrets/backend.yaml

local: secrets prod

clean:
	docker compose down

healthcheck: prod clean

.PHONY: tests secrets

tests: healthcheck
	cd tests && uv sync && uv run pytest

watch:
	docker compose watch
