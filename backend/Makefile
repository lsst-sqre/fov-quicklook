.PHONY: test test/cov-server

test:
	./.venv/bin/pytest

test/cov-server:
	./.venv/bin/python -m http.server -d htmlcov 4000
