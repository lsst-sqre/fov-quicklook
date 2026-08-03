#!/bin/sh

set -eu

session=${FQ_DEV_BACKEND_TMUX_SESSION:-dev}
repo_root=${FQ_REPO_ROOT:-/workspace/fov-quicklook}

usage() {
  cat <<'EOF'
Usage: sh dev/microk8s-dev/backend-restart.sh [all|coordinator|frontend-api|generator]
EOF
}

restart_window() {
  role=$1
  tmux respawn-window -k -t "${session}:${role}" fish
  tmux send-keys -t "${session}:${role}" "cd ${repo_root}; sh dev/microk8s-dev/backend-command.sh ${role}" C-m
}

role=${1:-all}
case "$role" in
  frontend)
    role=frontend-api
    ;;
esac

case "$role" in
  all)
    exec sh "${repo_root}/dev/microk8s-dev/backend-tmux.sh"
    ;;
  coordinator|frontend-api|generator)
    if ! tmux has-session -t "${session}" 2>/dev/null; then
      echo "tmux session not found: ${session}" >&2
      exit 1
    fi
    restart_window "$role"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
