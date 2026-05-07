#!/bin/sh

set -eu

if [ -n "${ENV_FILE:-}" ]; then
  if [ ! -f "$ENV_FILE" ]; then
    echo "ENV_FILE does not exist: $ENV_FILE" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

role=""
if [ $# -gt 0 ]; then
  case "$1" in
    frontend|coordinator|generator|bootstrap-db)
      role=$1
      shift
      ;;
  esac
fi

if [ -z "$role" ]; then
  role=${QUICKLOOK_REVIEW_APP_ROLE:-}
fi

case "$role" in
  frontend)
    exec python -m quicklook.frontend.api "$@"
    ;;
  coordinator)
    exec python -m quicklook.coordinator.api "$@"
    ;;
  generator)
    exec python -m quicklook.generator.api "$@"
    ;;
  bootstrap-db)
    exec python -m quicklook.scripts.bootstrap_db "$@"
    ;;
  "")
    exec "$@"
    ;;
  *)
    echo "unknown QUICKLOOK_REVIEW_APP_ROLE: $role" >&2
    exit 1
    ;;
esac
