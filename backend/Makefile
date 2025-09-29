.PHONY: test 
test:
	./.venv/bin/pytest

.PHONY: test/cov
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
