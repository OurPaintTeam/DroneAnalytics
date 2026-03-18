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

local: secrets prod

clean:
	docker compose down

healthcheck: prod clean

.PHONY: tests secrets

tests: healthcheck
	cd tests && uv sync && uv run pytest

watch:
	docker compose watch
