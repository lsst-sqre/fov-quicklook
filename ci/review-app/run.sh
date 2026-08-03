#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

usage() {
  cat <<'EOF'
Usage: ci/review-app/run.sh <command> [args...]

Commands:
  fixtures   Prepare shared fixtures
  bootstrap  Prepare gateway / registry access
  package    Build and push the review-app image
  deploy     Deploy the review app to Kubernetes
  smoke      Run the deployed review-app smoke check
  stop       Remove the deployed review app
  all        Run bootstrap -> package -> deploy -> smoke
EOF
}

command_name=${1:-all}
if [ $# -gt 0 ]; then
  shift
fi

case "$command_name" in
  fixtures)
    exec sh "$script_dir/prepare-shared-fixtures.sh" "$@"
    ;;
  bootstrap)
    exec sh "$script_dir/bootstrap-gateway.sh" "$@"
    ;;
  package)
    exec sh "$script_dir/package.sh" "$@"
    ;;
  deploy)
    exec sh "$script_dir/deploy.sh" "$@"
    ;;
  smoke)
    exec sh "$script_dir/smoke.sh" "$@"
    ;;
  stop)
    exec sh "$script_dir/stop.sh" "$@"
    ;;
  all)
    sh "$script_dir/bootstrap-gateway.sh" "$@"
    sh "$script_dir/package.sh" "$@"
    sh "$script_dir/deploy.sh" "$@"
    exec sh "$script_dir/smoke.sh" "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
