.PHONY: test 
test:
	uv run pytest

.PHONY: test/cov
test/cov:
	uv run pytest --cov=. --cov-report=html -m 'slow or not slow'

.PHONY: test/cov-server
test/cov-server:
	uv run python -m http.server -d htmlcov 4000

.PHONY: test/all
# Run all tests including those marked as slow. Overrides -m "not slow" from pytest.ini by passing an explicit -m all selector.
test/all:
	uv run pytest -m "not slow or slow"

.PHONY: pyright
pyright:
	uv run pyright src tests

.PHONY: pyright/watch
pyright/watch:
	uv run pyright --watch src tests

export ENV_FILE=./.dev.env

.PHONY: dev/coordinator
dev/coordinator:
	uv run uvicorn --reload quicklook.coordinator.api.app:app --port 9501 --no-access-log --reload-dir src

 .PHONY: dev/generator
dev/generator:
	uv run uvicorn --reload quicklook.generator.api.app:app --port 9502 --no-access-log --reload-dir src

 .PHONY: dev/generator2
dev/generator2:
	QUICKLOOK_generator_port=9600 uv run uvicorn --reload quicklook.generator.api.app:app --port 9600 --no-access-log --reload-dir src

.PHONY: dev/frontend
dev/frontend:
	uv run uvicorn --reload quicklook.frontend.api.app:app --port 9500 --no-access-log --reload-dir src


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

.PHONY: db/docker
db/docker:
	docker run --rm \
		--name quicklook-db \
		-e POSTGRES_USER=quicklook \
		-e POSTGRES_PASSWORD=quicklook \
		-e POSTGRES_DB=quicklook \
		-p 5432:5432 \
		-v "$(PWD)/docker-volumes/postgres:/var/lib/postgresql/data" \
		postgres:16 \
		-c log_statement=all \
		-c log_destination=stderr \
		-c log_line_prefix='%m [%p] %u@%d %r %a '


# --- デプロイ ---
# DEPLOY_BRANCH: ArgoCDが参照するイメージタグ（ブランチ名）。
# デフォルトは現在のgitブランチ。
# 注意: ブランチ名に「/」を含むとGitHub Actionsのビルドがトリガーされない。
DEPLOY_BRANCH ?= $(shell git branch --show-current)

.PHONY: deploy/push
deploy/push:
	git push

.PHONY: deploy/wait-build
deploy/wait-build:
	gh run watch --repo lsst-sqre/fov-quicklook

.PHONY: deploy/restart
deploy/restart:
	cd dev && ./argocd.sh restart

.PHONY: deploy/status
deploy/status:
	cd dev && ./argocd.sh status

.PHONY: deploy/healthz
deploy/healthz:
	cd dev && ./verify-deploy.sh healthz

.PHONY: deploy/set-branch
deploy/set-branch:
	cd dev && ./argocd.sh set-branch $(DEPLOY_BRANCH) --sync

.PHONY: deploy
deploy: deploy/push deploy/wait-build deploy/restart
	@echo ""
	@echo "=== デプロイ完了。30秒後に状態確認... ==="
	@sleep 30
	cd dev && ./argocd.sh status
	cd dev && ./verify-deploy.sh healthz