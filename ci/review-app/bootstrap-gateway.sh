#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "$script_dir/common.sh"

gateway_namespace=$(review_app_gateway_namespace)
gateway_name=$(review_app_gateway_name)
listener_name=$(review_app_gateway_listener_name)
gateway_address=$(review_app_gateway_address)
base_url=$(review_app_base_url)
image_registry=$(review_app_image_registry)
env_file=$(review_app_gitlab_env_file)
registry_namespace=$(review_app_registry_namespace)
registry_service_name=$(review_app_registry_service_name)

can_manage_microk8s_host() {
  [ "${REVIEW_APP_CONFIGURE_LOCAL_REGISTRY:-0}" = "1" ] || return 1
  [ -n "${REVIEW_APP_GATEWAY_ADDRESS:-}" ] || return 1
  [ -n "${REVIEW_APP_REGISTRY_HOST:-}" ] || return 1
  [ -n "${REVIEW_APP_REGISTRY_IP:-}" ] || return 1
  [ -n "${REVIEW_APP_MICROK8S_USER:-}" ] || return 1
}

ensure_microk8s_registry_host() {
  if ! can_manage_microk8s_host; then
    return 0
  fi

  host_line="${REVIEW_APP_REGISTRY_IP} ${REVIEW_APP_REGISTRY_HOST}"
  remote_cmd=$(cat <<REMOTE
set -eu
if ! grep -q -F '${host_line}' /etc/hosts; then
  printf '%s\n' '${host_line}' | sudo tee -a /etc/hosts >/dev/null
fi
REMOTE
)
  ssh -o StrictHostKeyChecking=no "${REVIEW_APP_MICROK8S_USER}@${REVIEW_APP_GATEWAY_ADDRESS}" "$remote_cmd"
}

wait_for_gateway_programmed() {
  for _ in $(seq 1 30); do
    programmed=$(kubectl -n "$gateway_namespace" get gateway "$gateway_name" \
      -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}' 2>/dev/null || true)
    if [ "$programmed" = "True" ]; then
      return 0
    fi
    sleep 2
  done

  echo "shared Gateway ${gateway_namespace}/${gateway_name} is not Programmed" >&2
  kubectl -n "$gateway_namespace" get gateway "$gateway_name" -o yaml >&2 || true
  return 1
}

ensure_microk8s_registry_host
kubectl wait -n "$registry_namespace" --for=condition=Available "deployment/${registry_service_name}" --timeout=180s
kubectl get namespace "$gateway_namespace" >/dev/null
kubectl -n "$gateway_namespace" get gateway "$gateway_name" >/dev/null
wait_for_gateway_programmed

listener=$(kubectl -n "$gateway_namespace" get gateway "$gateway_name" \
  -o jsonpath="{.spec.listeners[?(@.name==\"${listener_name}\")].name}" 2>/dev/null || true)
if [ "$listener" != "$listener_name" ]; then
  echo "shared Gateway ${gateway_namespace}/${gateway_name} does not expose listener ${listener_name}" >&2
  kubectl -n "$gateway_namespace" get gateway "$gateway_name" -o yaml >&2 || true
  exit 1
fi

cat > "$env_file" <<EOF
REVIEW_APP_GATEWAY_ADDRESS=${gateway_address}
REVIEW_APP_BASE_URL=${base_url}
REVIEW_APP_IMAGE_REGISTRY=${image_registry}
EOF
