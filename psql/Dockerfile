FROM postgres:16.13-alpine3.22-fips
# fun fact: fips - Federal Information Processing Standards (USE)
COPY dump.sql /docker-entrypoint-initdb.d/01-dump.sql
COPY secret.sql /docker-entrypoint-initdb.d/02-secret.sql

# already is not root