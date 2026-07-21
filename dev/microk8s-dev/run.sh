#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd -P)
repo_root=$(CDPATH= cd -- "${script_dir}/../.." && pwd -P)

namespace=${FQ_DEV_NAMESPACE:-fov-quicklook-dev}
source_root=${FQ_DEV_SOURCE_ROOT:-${repo_root}}
base_path=${FQ_DEV_BASE_PATH:-/fov-quicklook-dev}
backend_name=${FQ_DEV_BACKEND_NAME:-backend-dev}
frontend_name=${FQ_DEV_FRONTEND_NAME:-frontend-dev}
config_name=${FQ_DEV_CONFIG_NAME:-fov-quicklook-dev-config}
secret_name=${FQ_DEV_SECRET_NAME:-fov-quicklook-dev-secrets}
postgres_password=${FQ_DEV_POSTGRES_PASSWORD:-quicklook}
minio_access_key=${FQ_DEV_MINIO_ACCESS_KEY:-quicklook}
minio_secret_key=${FQ_DEV_MINIO_SECRET_KEY:-quicklook-secret}
tile_bucket=${FQ_DEV_TILE_BUCKET:-quicklook-tile}
test_data_bucket=${FQ_DEV_TEST_DATA_BUCKET:-quicklook-test-data}
dummy_visit_count=${FQ_DEV_DUMMY_VISIT_COUNT:-3}

usage() {
  cat <<'EOF'
Usage: dev/microk8s-dev/run.sh <command>

Commands:
  build-image  Build and import the dev toolbox image
  deploy       Deploy support services and sleeping dev pods
  start        Start backend/frontend dev servers inside tmux
  stop         Delete the dev namespace
  status       Show dev namespace resources
  all          Run build-image -> deploy -> start
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "required command not found: $1" >&2
    exit 1
  fi
}

ensure_source_root() {
  if [ ! -f "${source_root}/backend/pyproject.toml" ] || [ ! -f "${source_root}/frontend/app/package.json" ]; then
    echo "source tree not found at ${source_root}" >&2
    exit 1
  fi
}

image_ref() {
  if [ -n "${FQ_DEV_IMAGE:-}" ]; then
    printf '%s\n' "${FQ_DEV_IMAGE}"
    return
  fi

  printf '%s\n' "${FQ_DEV_IMAGE_REPOSITORY:-fov-quicklook/dev-pod}:${FQ_DEV_IMAGE_TAG:-dev}"
}

build_image() {
  require_command docker
  require_command sudo
  ensure_source_root

  image=$(image_ref)
  git_revision=$(git -C "${repo_root}" rev-parse HEAD 2>/dev/null || printf 'local\n')

  docker build \
    --build-arg "GIT_REVISION=${git_revision}" \
    -f "${script_dir}/Dockerfile" \
    -t "${image}" \
    "${repo_root}"
  docker save "${image}" | sudo microk8s ctr images import -
}

deploy_support() {
  image=$(image_ref)

  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: ${namespace}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${config_name}
  namespace: ${namespace}
data:
  FQ_REPO_ROOT: /workspace/fov-quicklook
  QUICKLOOK_admin_page: "true"
  QUICKLOOK_butler_scopes: '[{"dataset_type":"raw","display_name":"Raw","collection":"LSSTCam/raw/all","repository_name":"reviewapp-ci","instrument":"LSSTCam"}]'
  QUICKLOOK_coordinator_base_url: http://127.0.0.1:9501
  QUICKLOOK_data_source: dummy
  QUICKLOOK_environment: development
  QUICKLOOK_frontend_app_prefix: ${base_path}
  QUICKLOOK_s3_test_data__bucket: ${test_data_bucket}
  QUICKLOOK_s3_test_data__endpoint: minio:9000
  QUICKLOOK_s3_test_data__secure: "false"
  QUICKLOOK_s3_test_data__type: minio
  QUICKLOOK_s3_tile__bucket: ${tile_bucket}
  QUICKLOOK_s3_tile__endpoint: minio:9000
  QUICKLOOK_s3_tile__secure: "false"
  QUICKLOOK_s3_tile__type: minio
  VITE_API_PROXY_TARGET: http://${backend_name}:9500
  VITE_BASE_URL: ${base_path}
---
apiVersion: v1
kind: Secret
metadata:
  name: ${secret_name}
  namespace: ${namespace}
type: Opaque
stringData:
  MINIO_ROOT_PASSWORD: ${minio_secret_key}
  MINIO_ROOT_USER: ${minio_access_key}
  POSTGRES_DB: quicklook
  POSTGRES_PASSWORD: ${postgres_password}
  POSTGRES_USER: quicklook
  QUICKLOOK_db_url: postgresql+asyncpg://quicklook:${postgres_password}@postgres:5432/quicklook
  QUICKLOOK_s3_test_data__access_key: ${minio_access_key}
  QUICKLOOK_s3_test_data__secret_key: ${minio_secret_key}
  QUICKLOOK_s3_tile__access_key: ${minio_access_key}
  QUICKLOOK_s3_tile__secret_key: ${minio_secret_key}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: ${namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        envFrom:
        - secretRef:
            name: ${secret_name}
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
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: minio
  template:
    metadata:
      labels:
        app.kubernetes.io/name: minio
    spec:
      containers:
      - name: minio
        image: quay.io/minio/minio:RELEASE.2024-10-13T13-34-11Z
        args: ["server", "/data", "--address", ":9000"]
        envFrom:
        - secretRef:
            name: ${secret_name}
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
  ports:
  - name: http
    port: 9000
    targetPort: http
EOF

  kubectl -n "${namespace}" rollout status deployment/postgres --timeout=300s
  kubectl -n "${namespace}" rollout status deployment/minio --timeout=300s

  kubectl -n "${namespace}" delete job seed-fixtures bootstrap-db --ignore-not-found=true --wait=true

  cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-fixtures
  namespace: ${namespace}
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: seed-fixtures
        image: ${image}
        imagePullPolicy: IfNotPresent
        envFrom:
        - configMapRef:
            name: ${config_name}
        - secretRef:
            name: ${secret_name}
        command:
        - python
        - -m
        - quicklook.review_app.shared_fixtures
        - --root
        - /work/fixtures
        - --visit-count
        - "${dummy_visit_count}"
        - --overwrite
        - --seed-s3
        - --ensure-tile-bucket
        volumeMounts:
        - name: work
          mountPath: /work
      volumes:
      - name: work
        emptyDir: {}
---
apiVersion: batch/v1
kind: Job
metadata:
  name: bootstrap-db
  namespace: ${namespace}
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: bootstrap-db
        image: ${image}
        imagePullPolicy: IfNotPresent
        envFrom:
        - configMapRef:
            name: ${config_name}
        - secretRef:
            name: ${secret_name}
        command:
        - sh
        - -ceu
        - |
          cd /app
          python -m quicklook.scripts.bootstrap_db
EOF

  kubectl -n "${namespace}" wait --for=condition=Complete job/seed-fixtures --timeout=600s
  kubectl -n "${namespace}" wait --for=condition=Complete job/bootstrap-db --timeout=600s
}

deploy_dev_pods() {
  image=$(image_ref)

  cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${backend_name}
  namespace: ${namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: ${backend_name}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ${backend_name}
    spec:
      containers:
      - name: backend
        image: ${image}
        imagePullPolicy: IfNotPresent
        envFrom:
        - configMapRef:
            name: ${config_name}
        - secretRef:
            name: ${secret_name}
        workingDir: /workspace/fov-quicklook
        ports:
        - name: frontend-api
          containerPort: 9500
        - name: coordinator
          containerPort: 9501
        - name: generator
          containerPort: 9502
        volumeMounts:
        - name: source
          mountPath: /workspace/fov-quicklook
        - name: workdir
          mountPath: /tmp/quicklook
      volumes:
      - name: source
        hostPath:
          path: ${source_root}
          type: Directory
      - name: workdir
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: ${backend_name}
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: ${backend_name}
  ports:
  - name: frontend-api
    port: 9500
    targetPort: frontend-api
  - name: coordinator
    port: 9501
    targetPort: coordinator
  - name: generator
    port: 9502
    targetPort: generator
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${frontend_name}
  namespace: ${namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: ${frontend_name}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ${frontend_name}
    spec:
      containers:
      - name: frontend
        image: ${image}
        imagePullPolicy: IfNotPresent
        envFrom:
        - configMapRef:
            name: ${config_name}
        - secretRef:
            name: ${secret_name}
        workingDir: /workspace/fov-quicklook
        ports:
        - name: vite
          containerPort: 5173
        volumeMounts:
        - name: source
          mountPath: /workspace/fov-quicklook
      volumes:
      - name: source
        hostPath:
          path: ${source_root}
          type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: ${frontend_name}
  namespace: ${namespace}
spec:
  selector:
    app.kubernetes.io/name: ${frontend_name}
  ports:
  - name: vite
    port: 5173
    targetPort: vite
EOF

  kubectl -n "${namespace}" rollout restart deployment/"${backend_name}" deployment/"${frontend_name}" >/dev/null
  kubectl -n "${namespace}" rollout status deployment/"${backend_name}" --timeout=300s
  kubectl -n "${namespace}" rollout status deployment/"${frontend_name}" --timeout=300s
}

deploy() {
  require_command kubectl
  ensure_source_root
  deploy_support
  deploy_dev_pods
}

start() {
  require_command kubectl
  kubectl -n "${namespace}" exec deploy/"${backend_name}" -- sh -lc 'cd /workspace/fov-quicklook && sh dev/microk8s-dev/backend-tmux.sh'
  kubectl -n "${namespace}" exec deploy/"${frontend_name}" -- sh -lc 'cd /workspace/fov-quicklook && sh dev/microk8s-dev/frontend-tmux.sh'
}

stop() {
  require_command kubectl
  kubectl delete namespace "${namespace}" --ignore-not-found=true
}

status() {
  require_command kubectl
  kubectl -n "${namespace}" get pods,svc,jobs
}

command_name=${1:-all}

case "${command_name}" in
  build-image)
    build_image
    ;;
  deploy)
    deploy
    ;;
  start)
    start
    ;;
  stop)
    stop
    ;;
  status)
    status
    ;;
  all)
    build_image
    deploy
    start
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
