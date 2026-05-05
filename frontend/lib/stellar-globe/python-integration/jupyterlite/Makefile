.PHONY: rebuild rebuild-python rebuild-jupyterlab-extension rebuild-dependencies serve rebuild-app

python_home := ./.venv
base_python = ~/miniconda3/envs/py3_12/bin/python

serve: rebuild
	$(python_home)/bin/jupyter lite serve

rebuild: rebuild-dependencies
	$(MAKE) build

build:
	mkdir -p pypi files
	cp ../python/dist/hscmap-0.0.0-py3-none-any.whl ./pypi/
	cp ../jupyterlab-extension/tutorial.ipynb ./files/
	$(python_home)/bin/pip uninstall -y stellar_globe_jupyterlab_extension
	$(python_home)/bin/pip install ../jupyterlab-extension
	$(python_home)/bin/jupyter lite build

rebuild-dependencies: rebuild-python rebuild-jupyterlab-extension

rebuild-app:
	$(MAKE) -C ../../app lib

rebuild-python: rebuild-app
	$(MAKE) -C ../python build

rebuild-jupyterlab-extension: rebuild-app
	$(MAKE) -C ../jupyterlab-extension build

deploy: rebuild
	rsync -av --delete _output/ hscmap.mtk.nao.ac.jp:htdocs/hscMap5/jupyter/

.venv:
	$(base_python) -m venv .venv

setup: .venv 
	$(python_home)/bin/pip install -U pip
	$(python_home)/bin/pip install jupyterlab
	$(python_home)/bin/pip install jupyterlite-core
	$(python_home)/bin/pip install jupyterlite-pyodide-kernel
