python_home := ./.venv
base_python = ~/miniconda3/envs/py3_12/bin/python

build:
	$(python_home)/bin/python -m build

deploy: build
	chmod 644 ./dist/*.tar.gz
	ssh hscmap.mtk.nao.ac.jp mkdir -p htdocs/hscMap5/python/dist
	rsync -av ./dist/ hscmap.mtk.nao.ac.jp:htdocs/hscMap5/python/dist

.venv:
	$(base_python) -m venv .venv

setup: .venv
	$(python_home)/bin/pip install -U pip
	$(python_home)/bin/pip install -e .
	$(python_home)/bin/pip install -e '.[dev]'
