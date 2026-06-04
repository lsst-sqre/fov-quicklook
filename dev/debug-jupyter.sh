#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../backend"

if [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    PYTHON="${BACKEND_DIR}/.venv/bin/python"
else
    PYTHON="python3"
fi

PYTHONPATH="${BACKEND_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    exec "${PYTHON}" -m quicklook.dev.debug_jupyter "$@"
