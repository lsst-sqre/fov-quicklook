#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"

if [[ -z "$APP_BRANCH" ]]; then
    echo "エラー: detached HEAD では deploy-current.sh を使えません。" >&2
    exit 1
fi

uv run --project "$REPO_ROOT/dev/deploy-broker" deploy-broker-verify \
    --deploy-name "$APP_BRANCH" \
    --app-repo "$REPO_ROOT" \
    --deploy-poll-seconds 5 \
    "$@"

uv run --project "$REPO_ROOT/dev/deploy-broker" deploy-broker-client argocd-status
