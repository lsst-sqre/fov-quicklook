#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN=$(cat "$SCRIPT_DIR/.argocd-token")
ARGOCD_BASE="https://usdf-rsp-dev.slac.stanford.edu/argo-cd"
APP_NAME="fov-quicklook"
APP_NAMESPACE="fov-quicklook"
DEPLOYMENT="fov-quicklook-generator"

# Get all generator pod names
POD_NAMES=$(curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/resource-tree" \
    -H "Cookie: argocd.token=${TOKEN}" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for n in data.get('nodes', []):
    if n['kind'] == 'Pod' and n.get('name', '').startswith('${DEPLOYMENT}-'):
        print(n['name'])
")

for pod_name in $POD_NAMES; do
    echo "=== ログ: $pod_name ===" >&2
    curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/logs?namespace=${APP_NAMESPACE}&podName=${pod_name}&container=${DEPLOYMENT}&sinceSeconds=600" \
        -H "Cookie: argocd.token=${TOKEN}" \
        | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        data = json.loads(line)
        print(data['result']['content'])
    except:
        pass
"
done
