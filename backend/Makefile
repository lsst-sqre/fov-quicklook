.PHONY: test test/watch test/covhtml-server pyright pyright/watch db/create-migration db/migrate db/rollback db/docker 

targets ?= tests

test:
	./.venv/bin/python -m pytest \
		$(test_opts) \
		--failed-first -x \
		--cov=quicklook \
		--cov-report=html \
		--tb=short \
		$(targets)

test/watch:
	./.venv/bin/ptw --runner "$(MAKE) test"

test/covhtml-server:
	./.venv/bin/python -m http.server -d ./htmlcov 4000

pyright:
	[ -x ./pyright/node_modules/.bin/pyright ] || ( mkdir -p pyright && cd pyright && npm install pyright  )
	find src tests -name '*.py' | xargs ./pyright/node_modules/.bin/pyright --pythonpath ./.venv/bin/python

pyright/watch:
	[ -x ./pyright/node_modules/.bin/pyright ] || ( mkdir -p pyright && cd pyright && npm install pyright  )
	find src tests -name '*.py' | xargs ./pyright/node_modules/.bin/pyright --pythonpath ./.venv/bin/python --watch

db/create-migration:
	@ [ "$(message)" ] || (echo "message is not set" && false)
	./.venv/bin/alembic revision --autogenerate -m "$(message)"

db/migrate:
	./.venv/bin/alembic upgrade head

db/rollback:
	./.venv/bin/alembic downgrade -1

db/docker:
	docker run --rm \
		--name quicklook-db \
		-e POSTGRES_USER=quicklook \
		-e POSTGRES_PASSWORD=quicklook \
		-e POSTGRES_DB=quicklook \
		-p 5432:5432 \
		-v $(PWD)/docker-volumes/postgres:/var/lib/postgresql/data \
		postgres:16

dev/openapi:
	@QUICKLOOK_admin_page=True \
		./.venv/bin/python -m quicklook.frontend.api.openapi
