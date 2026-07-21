#!/bin/sh

set -eu

repo_root=${FQ_REPO_ROOT:-/workspace/fov-quicklook}
frontend_root="${repo_root}/frontend/app"
stellar_globe_root="${repo_root}/frontend/lib/stellar-globe"

ensure_npm_deps() {
  target_dir=$1
  if [ ! -d "${target_dir}/node_modules" ]; then
    cd "${target_dir}"
    npm ci
  fi
}

if [ ! -f "${frontend_root}/package.json" ]; then
  echo "frontend checkout not found: ${frontend_root}" >&2
  exit 1
fi

if [ ! -f "${stellar_globe_root}/stellar-globe/package.json" ] || [ ! -f "${stellar_globe_root}/react-stellar-globe/package.json" ]; then
  echo "stellar-globe checkout not found under ${stellar_globe_root}" >&2
  exit 1
fi

ensure_npm_deps "${stellar_globe_root}/stellar-globe"
cd "${stellar_globe_root}/stellar-globe"
npm run build

ensure_npm_deps "${stellar_globe_root}/react-stellar-globe"
cd "${stellar_globe_root}/react-stellar-globe"
npm run build

ensure_npm_deps "${frontend_root}"
cd "$frontend_root"

export VITE_BASE_URL="${VITE_BASE_URL:-/fov-quicklook-dev}"
export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://backend-dev:9500}"

exec npm run dev -- --host 0.0.0.0 --port "${VITE_DEV_PORT:-5173}" "$@"
