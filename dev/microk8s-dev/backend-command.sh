#!/bin/sh

set -eu

repo_root=${FQ_REPO_ROOT:-/workspace/fov-quicklook}
backend_root="${repo_root}/backend"
python_bin=${FQ_DEV_PYTHON:-/app/.venv/bin/python}

usage() {
  cat <<'EOF'
Usage: sh dev/microk8s-dev/backend-command.sh <frontend-api|coordinator|generator|bootstrap-db> [args...]
EOF
}

if [ ! -f "${backend_root}/pyproject.toml" ]; then
  echo "backend checkout not found: ${backend_root}" >&2
  exit 1
fi

if [ ! -x "${python_bin}" ]; then
  echo "python executable not found: ${python_bin}" >&2
  exit 1
fi

run_uvicorn() {
  module=$1
  port=$2
  shift 2
  exec "${python_bin}" -m uvicorn "$module" --host 0.0.0.0 --port "$port" --no-access-log --reload --reload-dir "${backend_root}/src" "$@"
}

role=${1:-}
if [ -z "$role" ]; then
  usage >&2
  exit 1
fi
shift

cd "$backend_root"
export PYTHONPATH="${backend_root}/src${PYTHONPATH:+:${PYTHONPATH}}"

case "$role" in
  frontend|frontend-api)
    run_uvicorn quicklook.frontend.api.app:app 9500 "$@"
    ;;
  coordinator)
    run_uvicorn quicklook.coordinator.api.app:app 9501 "$@"
    ;;
  generator)
    run_uvicorn quicklook.generator.api.app:app 9502 "$@"
    ;;
  bootstrap-db)
    exec "${python_bin}" -m quicklook.scripts.bootstrap_db "$@"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
