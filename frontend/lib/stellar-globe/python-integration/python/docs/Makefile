# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= ../.venv/bin/sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile watch build autodoc deploy

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

watch:
	$(MAKE) build
	../.venv/bin/watchmedo shell-command --patterns="*.py;*.rst" --recursive --command='$(MAKE) build' -W . ../src/hscmap

build:
	$(MAKE) autodoc
	$(MAKE) html

autodoc:
	rm -rf autodoc
	../.venv/bin/sphinx-apidoc -d 1 --separate -f -o ./autodoc ../src/hscmap ../src/hscmap/comm ../src/hscmap/models ../src/hscmap/jsonpatchapply.py

deploy: build
	ssh hscmap.mtk.nao.ac.jp mkdir -p htdocs/hscMap5/python/docs/
	rsync -av --delete ./_build/html/ hscmap.mtk.nao.ac.jp:htdocs/hscMap5/python/docs/
