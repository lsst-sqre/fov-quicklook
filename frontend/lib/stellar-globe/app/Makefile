.PHONY: all lib standalone toapp-typevalidator action-typevalidator persistent-typevalidator deploy public-jsonschema

all: standalone lib public-jsonschema

lib: toapp-typevalidator action-typevalidator persistent-typevalidator
	npm run build-lib

standalone: persistent-typevalidator
	npm run build-standalone

toapp-typevalidator: node_modules
	npm run make-toapp-typevalidator

action-typevalidator: node_modules
	npm run make-action-typevalidator

persistent-typevalidator: node_modules
	npm run make-persistent-typevalidator

deploy: standalone
	rsync -av --delete ./dist/standalone/ hscmap.mtk.nao.ac.jp:htdocs/hscMap5/app/

# This is for Python module
public-jsonschema:
	npm run make-public-json-schema

node_modules: package.json package-lock.json
	npm install

s23b_validation: standalone
	rsync --delete -av ./dist/standalone/ 133.40.210.20:/usr/share/nginx/html/hsc_ssp/dr4/s23b/validation/hscmap-b4eac0dd1a53a105/app/
