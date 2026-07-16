DEV_COMPOSE = docker compose -f _docker/docker-compose.dev.yml --env-file .env

.PHONY: dev-build dev-superuser


# Setup (run once)

network:
	docker network create fintech 2>/dev/null || true


# Dev

dev-build: network
	$(DEV_COMPOSE) up -d --build

dev-superuser:
	$(DEV_COMPOSE) exec backend python3 manage.py createsuperuser


# Django

startapp:
	uv run python manage.py startapp ${app}

