image_ref := localhost:32000/quicklook

.PHONY: build push deploy dev-update restart

build:
	$(MAKE) -C backend pyright
	docker build -t $(image_ref) .

push: build
	docker push $(image_ref)

restart:
	kubectl -n quicklook rollout restart deployment fov-quicklook-coordinator
	kubectl -n quicklook rollout restart deployment fov-quicklook-frontend
	kubectl -n quicklook rollout restart deployment fov-quicklook-generator

deploy: push restart

dev-update:
	helm upgrade --install  --create-namespace -n quicklook quicklook ./k8s/quicklook \
		--debug \
		--set global.vaultSecretsPathPrefix=secret \
		--set use_gafaelfawr=false \
		--set image.repository=$(image_ref) \
		--set image.tag=latest \
		--set data_source=dummy \
		-f ./notes/dev-values.yaml

push-to-ghcr: build
	docker tag $(image_ref) ghcr.io/michitaro/rubin-fov-viewer
	docker push ghcr.io/michitaro/rubin-fov-viewer