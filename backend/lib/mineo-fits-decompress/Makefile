
.PHONY: install build test test/watch

install: build
	./.venv/bin/python setup.py install

build:
	CC=/opt/rh/devtoolset-10/root/bin/gcc ./.venv/bin/python setup.py build

test: install
	./.venv/bin/python -m pytest -s

test/watch:
	./.venv/bin/ptw --runner "$(MAKE) test" fuse-fitsfs tests
