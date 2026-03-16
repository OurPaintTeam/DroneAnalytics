all: prod

prod:
	docker compose up -d --build

env:
	printf "DRONE_CORS_ORIGINS=*\nDRONE_API_KEY=change-me\n" > ./backend/.env

# It's just a example of certs. It's not for production. IT'S FOR LOCAL TESTS
secrets:
	openssl req -x509 -nodes -days 365 \
		-newkey rsa:2048 \
		-keyout secrets/proxy.key \
		-out secrets/proxy.crt \
		-subj "/CN=localhost"

local: env secrets prod

clean:
	docker compose down

healthcheck: prod clean

.PHONY: tests

tests: healthcheck
	cd tests && uv sync && uv run pytest

watch:
	docker compose watch