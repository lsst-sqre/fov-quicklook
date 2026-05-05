python_home := ./.venv
base_python = ~/miniconda3/envs/py3_12/bin/python

.PHONE: setup test test-watch datamodel typecheck typecheck-watch deploy build

build:
	$(python_home)/bin/python -m build

.venv:
	$(base_python) -m venv .venv

setup: .venv
	$(python_home)/bin/pip install -U pip
	$(python_home)/bin/pip install -e .
	$(python_home)/bin/pip install -e '.[dev]'

test:
	$(python_home)/bin/pytest --cov=hscmap --cov-report=html --ff -x -s tests $(pytest_opts)

test-watch:
	$(python_home)/bin/ptw --runner "$(MAKE) test"

../../app/jsonschema/public.json:
	$(MAKE) -C ../../app public-jsonschema

datamodel: ../../app/jsonschema/public.json
	$(python_home)/bin/python -m devel.gendatamodel

typecheck:
	./node_modules/.bin/pyright --pythonpath $(python_home)/bin/python ./src/hscmap

typecheck-watch:
	./node_modules/.bin/pyright --watch --pythonpath $(python_home)/bin/python ./src/hscmap

deploy: build
	ssh hscmap.mtk.nao.ac.jp mkdir -p htdocs/hscMap5/python/dist
	rsync -av ./dist/ hscmap.mtk.nao.ac.jp:htdocs/hscMap5/python/dist
