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
    exec "${python_bin}" -m uvicorn quicklook.frontend.api.app:app --host 0.0.0.0 --port 9500 --no-access-log "$@"
    ;;
  coordinator)
    exec "${python_bin}" -m uvicorn quicklook.coordinator.api.app:app --host 0.0.0.0 --port 9501 --no-access-log "$@"
    ;;
  generator)
    exec "${python_bin}" -m uvicorn quicklook.generator.api.app:app --host 0.0.0.0 --port 9502 --no-access-log "$@"
    ;;
  bootstrap-db)
    exec "${python_bin}" -m quicklook.scripts.bootstrap_db "$@"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
