#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "$script_dir/common.sh"

namespace=$(review_app_namespace)
route_name=$(review_app_route_name)
project_name=$(review_app_project_name)
project_path_slug=$(review_app_project_path_slug)
review_id=$(review_app_id)
base_path=$(review_app_base_path)
environment_url=$(review_app_environment_url)
base_url=$(review_app_base_url)
gateway_namespace=$(review_app_gateway_namespace)
gateway_name=$(review_app_gateway_name)
listener_name=$(review_app_gateway_listener_name)
gateway_address=$(review_app_gateway_address)
image=$(review_app_image)
env_file=$(review_app_gitlab_env_file)
data_source=$(review_app_data_source)
fixture_path=$(review_app_shared_fixture_path)
fixture_env_file=$(review_app_fixture_env_file)
generator_replicas=$(review_app_generator_replicas)
repository_name=$(review_app_repository_name)
sample_exposure_id=$(review_app_sample_exposure_id)
dummy_visit_count=$(review_app_dummy_visit_count)
butler_visit_count=$(review_app_butler_visit_count)

postgres_password=${REVIEW_APP_POSTGRES_PASSWORD:-quicklook}
minio_access_key=${REVIEW_APP_MINIO_ACCESS_KEY:-reviewapp}
minio_secret_key=${REVIEW_APP_MINIO_SECRET_KEY:-reviewapp-secret}
postgres_image=${REVIEW_APP_POSTGRES_IMAGE:-postgres:16-alpine}
minio_image=${REVIEW_APP_MINIO_IMAGE:-quay.io/minio/minio:RELEASE.2024-10-13T13-34-11Z}
tile_bucket=${REVIEW_APP_TILE_BUCKET:-quicklook-tile}
test_data_bucket=${REVIEW_APP_TEST_DATA_BUCKET:-quicklook-test-data}
seed_s3_flag=""

if [ "$data_source" = "dummy" ]; then
  seed_s3_flag="--seed-s3"
fi

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: ${namespace}
  labels:
    app.kubernetes.io/part-of: ${project_name}
    app.gitlab.com/env: review
    app.gitlab.com/project: ${project_path_slug}
    review-app.id: ${review_id}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: review-app-config
  namespace: ${namespace}
data:
  ENV_FILE: ${fixture_env_file}
  QUICKLOOK_admin_page: "true"
  QUICKLOOK_environment: production
  QUICKLOOK_frontend_app_prefix: ${base_path}
  QUICKLOOK_frontend_assets_dir: /app/frontend-assets
  QUICKLOOK_coordinator_base_url: http://coordinator:9501
  QUICKLOOK_generate_single_fits_tiles_timeout_seconds: "300"
  QUICKLOOK_s3_tile__endpoint: minio:9000
  QUICKLOOK_s3_tile__bucket: ${tile_bucket}
  QUICKLOOK_s3_tile__secure: "false"
  QUICKLOOK_s3_tile__type: minio
  QUICKLOOK_s3_test_data__endpoint: minio:9000
  QUICKLOOK_s3_test_data__bucket: ${test_data_bucket}
  QUICKLOOK_s3_test_data__secure: "false"
  QUICKLOOK_s3_test_data__type: minio
---
apiVersion: v1
kind: Secret
metadata:
  name: review-app-secrets
  namespace: ${namespace}
type: Opaque
stringData:
  QUICKLOOK_db_url: postgresql+asyncpg://quicklook:${postgres_password}@postgres:5432/quicklook
  QUICKLOOK_s3_tile__access_key: ${minio_access_key}
  QUICKLOOK_s3_tile__secret_key: ${minio_secret_key}
  QUICKLOOK_s3_test_data__access_key: ${minio_access_key}
  QUICKLOOK_s3_test_data__secret_key: ${minio_secret_key}
  POSTGRES_DB: quicklook
  POSTGRES_USER: quicklook
  POSTGRES_PASSWORD: ${postgres_password}
  MINIO_ROOT_USER: ${minio_access_key}
  MINIO_ROOT_PASSWORD: ${minio_secret_key}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: postgres
    app.kubernetes.io/instance: ${review_id}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
      app.kubernetes.io/instance: ${review_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
        app.kubernetes.io/instance: ${review_id}
    spec:
      containers:
      - name: postgres
        image: ${postgres_image}
        envFrom:
        - secretRef:
            name: review-app-secrets
        ports:
        - name: postgres
          containerPort: 5432
        readinessProbe:
          exec:
            command: ["sh", "-c", "pg_isready -U quicklook -d quicklook"]
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          exec:
            command: ["sh", "-c", "pg_isready -U quicklook -d quicklook"]
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: postgres
    app.kubernetes.io/instance: ${review_id}
  ports:
  - name: postgres
    port: 5432
    targetPort: postgres
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: minio
    app.kubernetes.io/instance: ${review_id}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: minio
      app.kubernetes.io/instance: ${review_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: minio
        app.kubernetes.io/instance: ${review_id}
    spec:
      containers:
      - name: minio
        image: ${minio_image}
        args: ["server", "/data", "--address", ":9000"]
        envFrom:
        - secretRef:
            name: review-app-secrets
        ports:
        - name: http
          containerPort: 9000
        readinessProbe:
          httpGet:
            path: /minio/health/ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /minio/health/live
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: minio
    app.kubernetes.io/instance: ${review_id}
  ports:
  - name: http
    port: 9000
    targetPort: http
EOF

kubectl wait --for=jsonpath='{.status.phase}'=Active "namespace/${namespace}" --timeout=60s
kubectl -n "$namespace" rollout status deployment/postgres --timeout=300s
kubectl -n "$namespace" rollout status deployment/minio --timeout=300s

kubectl -n "$namespace" delete job seed-fixtures --ignore-not-found=true
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-fixtures
  namespace: ${namespace}
spec:
  backoffLimit: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: seed-fixtures
        app.kubernetes.io/instance: ${review_id}
    spec:
      restartPolicy: Never
      initContainers:
      - name: reset-butler-registry
        image: ${postgres_image}
        envFrom:
        - secretRef:
            name: review-app-secrets
        command:
        - sh
        - -ceu
        - |
          export PGPASSWORD="\${POSTGRES_PASSWORD}"
          until pg_isready -h postgres -U "\${POSTGRES_USER}" -d postgres; do
            sleep 2
          done
          psql -h postgres -U "\${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS butler_registry WITH (FORCE)"
          psql -h postgres -U "\${POSTGRES_USER}" -d postgres -c "CREATE DATABASE butler_registry"
          psql -h postgres -U "\${POSTGRES_USER}" -d butler_registry -c "CREATE EXTENSION IF NOT EXISTS btree_gist"
      containers:
      - name: seed-fixtures
        image: ${image}
        imagePullPolicy: Always
        command:
        - python
        - -m
        - quicklook.review_app.shared_fixtures
        - --root
        - ${fixture_path}
        - --visit-count
        - "${dummy_visit_count}"
        - --butler-visit-count
        - "${butler_visit_count}"
        - --butler-registry-url
        - postgresql://quicklook:${postgres_password}@postgres:5432/butler_registry
        - --ensure-tile-bucket
$(if [ -n "$seed_s3_flag" ]; then printf '        - %s\n' "$seed_s3_flag"; fi)
        env:
        - name: QUICKLOOK_s3_tile__endpoint
          value: minio:9000
        - name: QUICKLOOK_s3_tile__access_key
          value: ${minio_access_key}
        - name: QUICKLOOK_s3_tile__secret_key
          value: ${minio_secret_key}
        - name: QUICKLOOK_s3_tile__secure
          value: "false"
        - name: QUICKLOOK_s3_tile__bucket
          value: ${tile_bucket}
        - name: QUICKLOOK_s3_tile__type
          value: minio
        - name: QUICKLOOK_s3_test_data__endpoint
          value: minio:9000
        - name: QUICKLOOK_s3_test_data__access_key
          value: ${minio_access_key}
        - name: QUICKLOOK_s3_test_data__secret_key
          value: ${minio_secret_key}
        - name: QUICKLOOK_s3_test_data__secure
          value: "false"
        - name: QUICKLOOK_s3_test_data__bucket
          value: ${test_data_bucket}
        - name: QUICKLOOK_s3_test_data__type
          value: minio
        volumeMounts:
        - name: shared-fixtures
          mountPath: ${fixture_path}
      volumes:
      - name: shared-fixtures
        hostPath:
          path: ${fixture_path}
          type: DirectoryOrCreate
EOF

kubectl -n "$namespace" wait --for=condition=Complete job/seed-fixtures --timeout=600s

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coordinator
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: coordinator
    app.kubernetes.io/instance: ${review_id}
    app.kubernetes.io/part-of: ${project_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: coordinator
      app.kubernetes.io/instance: ${review_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: coordinator
        app.kubernetes.io/instance: ${review_id}
        app.kubernetes.io/part-of: ${project_name}
      annotations:
        review-app.commit: ${CI_COMMIT_SHA:-local}
        review-app.image: ${image}
    spec:
      initContainers:
      - name: wait-for-postgres
        image: ${postgres_image}
        envFrom:
        - secretRef:
            name: review-app-secrets
        command:
        - sh
        - -ceu
        - |
          until pg_isready -h postgres -U quicklook -d quicklook; do
            sleep 2
          done
      - name: bootstrap-db
        image: ${image}
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: review-app-config
        - secretRef:
            name: review-app-secrets
        command: ["fov-quicklook-review-app-entrypoint", "bootstrap-db"]
        volumeMounts:
        - name: shared-fixtures
          mountPath: ${fixture_path}
          readOnly: true
      containers:
      - name: coordinator
        image: ${image}
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: review-app-config
        - secretRef:
            name: review-app-secrets
        env:
        - name: QUICKLOOK_REVIEW_APP_ROLE
          value: coordinator
        ports:
        - name: http
          containerPort: 9501
        readinessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: shared-fixtures
          mountPath: ${fixture_path}
          readOnly: true
      volumes:
      - name: shared-fixtures
        hostPath:
          path: ${fixture_path}
          type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: coordinator
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: coordinator
    app.kubernetes.io/instance: ${review_id}
  ports:
  - name: http
    port: 9501
    targetPort: http
EOF

kubectl -n "$namespace" rollout status deployment/coordinator --timeout=600s

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: generator
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: generator
    app.kubernetes.io/instance: ${review_id}
    app.kubernetes.io/part-of: ${project_name}
spec:
  replicas: ${generator_replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: generator
      app.kubernetes.io/instance: ${review_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: generator
        app.kubernetes.io/instance: ${review_id}
        app.kubernetes.io/part-of: ${project_name}
      annotations:
        review-app.commit: ${CI_COMMIT_SHA:-local}
        review-app.image: ${image}
    spec:
      containers:
      - name: generator
        image: ${image}
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: review-app-config
        - secretRef:
            name: review-app-secrets
        env:
        - name: QUICKLOOK_REVIEW_APP_ROLE
          value: generator
        ports:
        - name: http
          containerPort: 9502
        readinessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: shared-fixtures
          mountPath: ${fixture_path}
          readOnly: true
        - name: workdir
          mountPath: /tmp/quicklook
      volumes:
      - name: shared-fixtures
        hostPath:
          path: ${fixture_path}
          type: DirectoryOrCreate
      - name: workdir
        emptyDir: {}
EOF

kubectl -n "$namespace" rollout status deployment/generator --timeout=600s

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: frontend
    app.kubernetes.io/instance: ${review_id}
    app.kubernetes.io/part-of: ${project_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: frontend
      app.kubernetes.io/instance: ${review_id}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: frontend
        app.kubernetes.io/instance: ${review_id}
        app.kubernetes.io/part-of: ${project_name}
      annotations:
        review-app.commit: ${CI_COMMIT_SHA:-local}
        review-app.image: ${image}
    spec:
      containers:
      - name: frontend
        image: ${image}
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: review-app-config
        - secretRef:
            name: review-app-secrets
        env:
        - name: QUICKLOOK_REVIEW_APP_ROLE
          value: frontend
        ports:
        - name: http
          containerPort: 9500
        readinessProbe:
          httpGet:
            path: ${base_path}/api/healthz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: ${base_path}/api/healthz
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: shared-fixtures
          mountPath: ${fixture_path}
          readOnly: true
      volumes:
      - name: shared-fixtures
        hostPath:
          path: ${fixture_path}
          type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: frontend
    app.kubernetes.io/instance: ${review_id}
  ports:
  - name: http
    port: 9500
    targetPort: http
EOF

kubectl -n "$namespace" rollout status deployment/frontend --timeout=600s

cat <<EOF | kubectl apply -f -
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: ${route_name}
  namespace: ${namespace}
  labels:
    app.kubernetes.io/name: review-app
    app.kubernetes.io/instance: ${review_id}
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: ${gateway_namespace}
  to:
  - group: ""
    kind: Service
    name: frontend
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: ${route_name}
  namespace: ${gateway_namespace}
  labels:
    app.kubernetes.io/name: review-app
    app.kubernetes.io/instance: ${review_id}
    app.kubernetes.io/part-of: ${project_name}
    app.gitlab.com/project: ${project_path_slug}
spec:
  parentRefs:
  - name: ${gateway_name}
    sectionName: ${listener_name}
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: ${base_path}
    backendRefs:
    - name: frontend
      namespace: ${namespace}
      port: 9500
EOF

cat > "$env_file" <<EOF
REVIEW_APP_GATEWAY_ADDRESS=${gateway_address}
REVIEW_APP_BASE_URL=${base_url}
REVIEW_APP_ENVIRONMENT_URL=${environment_url}
REVIEW_APP_DATA_SOURCE=${data_source}
REVIEW_APP_REPOSITORY_NAME=${repository_name}
REVIEW_APP_SAMPLE_EXPOSURE_ID=${sample_exposure_id}
EOF

printf 'Review app URL: %s\n' "$environment_url"
