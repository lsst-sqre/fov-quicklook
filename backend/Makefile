.PHONY: test 
test:
	./.venv/bin/pytest

.PHONY: test/cov
test/cov:
	./.venv/bin/pytest --cov=. --cov-report=html -m 'slow or not slow'

.PHONY: test/cov-server
test/cov-server:
	./.venv/bin/python -m http.server -d htmlcov 4000

.PHONY: test/all
# Run all tests including those marked as slow. Overrides -m "not slow" from pytest.ini by passing an explicit -m all selector.
test/all:
	./.venv/bin/pytest -m "not slow or slow"

.PHONY: pyright/setup
pyright/setup:
	mkdir -p pyright
	cd pyright && npm install pyright

.PHONY: pyright
pyright:
	[ -x ./pyright/node_modules/.bin/pyright ] || ( mkdir -p pyright && cd pyright && npm install pyright  )
	find src tests -name '*.py' | xargs ./pyright/node_modules/.bin/pyright --pythonpath ./.venv/bin/python

.PHONY: pyright/watch
pyright/watch:
	[ -x ./pyright/node_modules/.bin/pyright ] || ( mkdir -p pyright && cd pyright && npm install pyright  )
	find src tests -name '*.py' | xargs ./pyright/node_modules/.bin/pyright --pythonpath ./.venv/bin/python --watch

.PHONY: dev/coordinator
dev/coordinator:
	ENV_FILE=./.dev.env \
	./.venv/bin/uvicorn --reload quicklook.coordinator.api.app:app --port 9501 --no-access-log

 .PHONY: dev/generator
dev/generator:
	ENV_FILE=./.dev.env \
	./.venv/bin/uvicorn --reload quicklook.generator.api.app:app --port 9502 --no-access-log

.PHONY: dev/frontend
dev/frontend:
	ENV_FILE=./.dev.env \
	./.venv/bin/uvicorn --reload quicklook.frontend.api.app:app --port 9500 --no-access-log


.PHONY: dev/openapi
dev/openapi:
	QUICKLOOK_admin_page=True \
	QUICKLOOK_frontend_app_prefix= \
	ENV_FILE=./.dev.env \
	./.venv/bin/python -m quicklook.frontend.api.openapi
