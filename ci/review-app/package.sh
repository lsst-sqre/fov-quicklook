#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "$script_dir/common.sh"

if [ ! -f frontend/app/dist/index.html ]; then
  echo "frontend/app/dist/index.html not found; run the review frontend build first" >&2
  exit 1
fi

image_ref=$(review_app_image)
printf 'Review app image: %s\n' "$image_ref" >&2
printf '%s\n' "$image_ref"
