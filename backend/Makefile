.PHONY: test
test:
	uv run --extra dev python -m pytest

.PHONY: test/cov
test/cov:
	uv run --extra dev python -m pytest --cov=. --cov-report=html -m 'slow or not slow'

.PHONY: test/cov-server
test/cov-server:
	uv run python -m http.server -d htmlcov 4000

.PHONY: test/all
# Run all tests including those marked as slow. Overrides -m "not slow" from pytest.ini by passing an explicit -m all selector.
test/all:
	uv run --extra dev python -m pytest -m "not slow or slow"

.PHONY: pyright
pyright:
	uv run --extra dev pyright src tests

.PHONY: pyright/watch
pyright/watch:
	uv run --extra dev pyright --watch src tests

export ENV_FILE=./.dev.env

.PHONY: dev/openapi
dev/openapi:
	QUICKLOOK_admin_page=True \
	QUICKLOOK_frontend_app_prefix= \
	ENV_FILE=./.dev.env \
	uv run python -m quicklook.frontend.api.openapi


.PHONY: db/create-migration
db/create-migration:
	@ [ "$(message)" ] || (echo "message is not set" && false)
	uv run alembic revision --autogenerate -m "$(message)"

.PHONY: db/migrate
db/migrate:
	uv run alembic upgrade head

.PHONY: db/rollback
db/rollback:
	uv run alembic downgrade -1

.PHONY: db/bootstrap
db/bootstrap:
	uv run python -m quicklook.scripts.bootstrap_db