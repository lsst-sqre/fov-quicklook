#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)

shared_root="${REVIEW_APP_SHARED_FIXTURE_ROOT:-$repo_root/copilot/review-app-shared-fixtures}"

cd "$repo_root/backend"
uv run --frozen --no-dev python -m quicklook.review_app.shared_fixtures --root "$shared_root" "$@"
