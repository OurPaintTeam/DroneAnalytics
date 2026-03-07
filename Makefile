all: prod

prod:
	docker compose up -d --build

env:
	printf "DRONE_CORS_ORIGINS=*\nDRONE_API_KEY=change-me\n" > ./backend/.env
	printf "discovery.type=single-node\nxpack.security.enabled=false\nES_JAVA_OPTS=-Xms512m -Xmx512m\n" > ./elastic/.env
	printf "VITE_BACKEND_URL=https://localhost/api\n" > ./frontend/.env
	printf "ELASTIC_URL=http://elastic:9200" > ./init-elastic/.env
	([ -d "./proxy/certs" ] && echo "Certs already exist") || echo ""
	[ -d "./proxy/certs" ] || ( cd proxy && mkdir -p certs && cd certs && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout server.key -out server.crt && cd ../.. && echo "Create certs" )

local: env prod

clear:
	docker compose down

healthcheck: prod clear

tests: healthcheck
	echo "This will happen when Ivan is a good boy."
