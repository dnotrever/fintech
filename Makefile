DEV_COMPOSE = docker compose -f _docker/docker-compose.dev.yml --env-file .env

.PHONY: dev-build dev-superuser startapp superuser migrations migrate


# Setup (run once)

network:
	docker network create fintech 2>/dev/null || true


# Dev

dev-build: network
	$(DEV_COMPOSE) up -d --build


# Django

startapp:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py startapp ${app}

superuser:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py createsuperuser

migrations:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py makemigrations

migrate:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py migrate

