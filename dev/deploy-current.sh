#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"

if [[ -z "$APP_BRANCH" ]]; then
    echo "エラー: detached HEAD では deploy-current.sh を使えません。" >&2
    exit 1
fi

TRACKED_SUFFIX="$(printf '%s' "$APP_BRANCH" | tr -c '[:alnum:]._-' '-')"
TRACKED_SUFFIX="${TRACKED_SUFFIX#-}"
TRACKED_SUFFIX="${TRACKED_SUFFIX%-}"
TRACKED_SUFFIX="${TRACKED_SUFFIX:-manual}"
TRACKED_BRANCH="u/michitaro/fov-quicklook-${TRACKED_SUFFIX}"

uv run --project "$REPO_ROOT/dev/deploy-broker" deploy-broker-verify \
    --deploy-tracked-branch "$TRACKED_BRANCH" \
    --app-repo "$REPO_ROOT" \
    "$@"

uv run --project "$REPO_ROOT/dev/deploy-broker" deploy-broker-client argocd-status
