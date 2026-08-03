#!/bin/sh

set -eu

session=${FQ_DEV_FRONTEND_TMUX_SESSION:-dev}
repo_root=${FQ_REPO_ROOT:-/workspace/fov-quicklook}

tmux kill-session -t "${session}" 2>/dev/null || true
tmux new-session -d -s "${session}" -n vite fish
tmux send-keys -t "${session}:1" "cd ${repo_root}; sh dev/microk8s-dev/frontend-command.sh" C-m
