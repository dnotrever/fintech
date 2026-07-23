DEV_COMPOSE = docker compose -f _docker/docker-compose.dev.yml --env-file .env

.PHONY: dev-build dev-superuser startapp superuser migrations migrate dev-delete-user


# Setup (run once)

network:
	docker network create fintech 2>/dev/null || true


# Dev

dev-build: network
	$(DEV_COMPOSE) up -d --build

dev-superuser:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py createsuperuser

dev-migrate:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py migrate

dev-delete-user:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py delete_user ${user}

startapp:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py startapp ${app}

migrations:
	$(DEV_COMPOSE) exec backend uv run python3 manage.py makemigrations

