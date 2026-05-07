#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "$script_dir/common.sh"

environment_url=${REVIEW_APP_ENVIRONMENT_URL:-$(review_app_environment_url)}
repository_name=${REVIEW_APP_REPOSITORY_NAME:-$(review_app_repository_name)}
requested_visit=${REVIEW_APP_SAMPLE_VISIT_NAME:-}
base_url=${environment_url%/}

curl -fsS "${base_url}/api/healthz" >/dev/null

visits_json=$(curl -fsS "${base_url}/api/visits?data_type=raw&repository_name=${repository_name}&limit=10")
sample_visit=$(
  printf '%s' "$visits_json" | SMOKE_REQUESTED_VISIT="$requested_visit" python3 -c '
import json
import os
import sys

visits = json.load(sys.stdin)
if not visits:
    raise SystemExit("no visits returned from /api/visits")
requested = os.environ.get("SMOKE_REQUESTED_VISIT")
if requested:
    for visit in visits:
        if visit["id"] == requested:
            print(requested)
            break
    else:
        raise SystemExit(f"requested visit not found in /api/visits: {requested}")
else:
    print(visits[0]["id"])
'
)
sample_visit_path=$(printf '%s' "$sample_visit" | sed 's/:/%3A/g')

delete_status=$(
  curl -sS -o /dev/null -w '%{http_code}' \
    -X DELETE \
    "${base_url}/api/cache_entries/${sample_visit_path}"
)
case "$delete_status" in
  200|204|404)
    ;;
  *)
    printf 'failed to delete existing cache entry for %s (status=%s)\n' "$sample_visit" "$delete_status" >&2
    exit 1
    ;;
esac

curl -fsS \
  -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"visit\":\"${sample_visit}\"}" \
  "${base_url}/api/quicklooks" >/dev/null

for _ in $(seq 1 72); do
  metadata_json=$(curl -fsS "${base_url}/api/quicklooks/${sample_visit_path}/quicklook_metadata")
  metadata_state=$(
    printf '%s' "$metadata_json" | python3 -c '
import json
import sys

metadata = json.load(sys.stdin)
state = metadata.get("type")
if state == "ready":
    print("ready")
elif state == "error":
    print("error")
elif state == "progress":
    progress = metadata.get("progress") or {}
    if progress and all(step.get("count", 0) >= 2 for step in progress.values()):
        print("progress")
    else:
        print("pending")
else:
    print(state or "pending")
'
  )
  if [ "$metadata_state" = "ready" ]; then
    exit 0
  fi
  if [ "$metadata_state" = "error" ]; then
    printf 'quicklook generation failed: %s\n' "$metadata_json" >&2
    exit 1
  fi
  sleep 5
done

echo "timed out waiting for quicklook metadata to become ready" >&2
exit 1
