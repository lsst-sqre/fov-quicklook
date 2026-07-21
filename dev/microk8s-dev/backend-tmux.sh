#!/bin/sh

set -eu

session=${FQ_DEV_BACKEND_TMUX_SESSION:-dev}
repo_root=${FQ_REPO_ROOT:-/workspace/fov-quicklook}

tmux kill-session -t "${session}" 2>/dev/null || true

tmux new-session -d -s "${session}" -n coordinator fish
tmux new-window -t "${session}:" -n frontend-api fish
tmux new-window -t "${session}:" -n generator fish
tmux send-keys -t "${session}:1" "cd ${repo_root}; sh dev/microk8s-dev/backend-command.sh coordinator" C-m
tmux send-keys -t "${session}:2" "cd ${repo_root}; sh dev/microk8s-dev/backend-command.sh frontend-api" C-m
tmux send-keys -t "${session}:3" "cd ${repo_root}; sh dev/microk8s-dev/backend-command.sh generator" C-m
tmux select-window -t "${session}:1"
