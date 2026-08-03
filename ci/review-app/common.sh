#!/bin/sh

set -eu

review_app_project_name() {
  printf '%s\n' "${CI_PROJECT_NAME:-fov-quicklook2}"
}

review_app_project_path_slug() {
  if [ -n "${CI_PROJECT_PATH_SLUG:-}" ]; then
    printf '%s\n' "$CI_PROJECT_PATH_SLUG"
    return
  fi

  printf '%s\n' "$(review_app_project_name)" |
    tr '[:upper:]' '[:lower:]' |
    sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

review_app_id() {
  if [ -n "${REVIEW_APP_ID:-}" ]; then
    printf '%s\n' "$REVIEW_APP_ID"
    return
  fi
  if [ -n "${CI_MERGE_REQUEST_IID:-}" ]; then
    printf 'mr-%s\n' "$CI_MERGE_REQUEST_IID"
    return
  fi
  if [ -n "${CI_COMMIT_REF_SLUG:-}" ]; then
    printf '%s\n' "$CI_COMMIT_REF_SLUG"
    return
  fi
  printf 'local\n'
}

review_app_base_path() {
  if [ -n "${REVIEW_APP_BASE_PATH:-}" ]; then
    printf '%s\n' "$REVIEW_APP_BASE_PATH"
    return
  fi

  printf '/review-apps/%s/%s\n' "$(review_app_project_path_slug)" "$(review_app_id)"
}

review_app_namespace() {
  if [ -n "${REVIEW_APP_NAMESPACE:-}" ]; then
    printf '%s\n' "$REVIEW_APP_NAMESPACE"
    return
  fi

  base_name="review-$(review_app_project_path_slug)-$(review_app_id)"
  normalized=$(
    printf '%s' "$base_name" |
      tr '[:upper:]' '[:lower:]' |
      sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
  )
  checksum=$(printf '%s' "$normalized" | cksum | awk '{print $1}')
  prefix=$(printf '%.52s' "$normalized" | sed 's/-$//')
  printf '%s-%s' "$prefix" "$checksum" | cut -c1-63 | sed 's/-$//'
  printf '\n'
}

review_app_route_name() {
  base_name="$(review_app_project_path_slug)-$(review_app_id)"
  normalized=$(
    printf '%s' "$base_name" |
      tr '[:upper:]' '[:lower:]' |
      sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
  )
  checksum=$(printf '%s' "$normalized" | cksum | awk '{print $1}')
  prefix=$(printf '%.52s' "$normalized" | sed 's/-$//')
  printf '%s-%s' "$prefix" "$checksum" | cut -c1-63 | sed 's/-$//'
  printf '\n'
}

review_app_gateway_namespace() {
  printf '%s\n' "${REVIEW_APP_GATEWAY_NAMESPACE:-gateway-test}"
}

review_app_gateway_name() {
  printf '%s\n' "${REVIEW_APP_GATEWAY_NAME:-microk8s-envoy}"
}

review_app_gateway_class_name() {
  printf '%s\n' "${REVIEW_APP_GATEWAY_CLASS_NAME:-envoy}"
}

review_app_gateway_listener_name() {
  printf '%s\n' "${REVIEW_APP_GATEWAY_LISTENER_NAME:-http}"
}

review_app_detect_node_ip() {
  detect_script="$script_dir/detect-k8s-node-internal-ip.sh"

  if [ ! -f "$detect_script" ] || ! command -v kubectl >/dev/null 2>&1; then
    echo "review app node IP auto-detection is unavailable; set REVIEW_APP_GATEWAY_ADDRESS" >&2
    exit 1
  fi

  sh "$detect_script"
}

review_app_gateway_address() {
  if [ -n "${REVIEW_APP_GATEWAY_ADDRESS:-}" ]; then
    printf '%s\n' "$REVIEW_APP_GATEWAY_ADDRESS"
    return
  fi

  review_app_detect_node_ip
}

review_app_base_url() {
  if [ -n "${REVIEW_APP_BASE_URL:-}" ]; then
    printf '%s\n' "$REVIEW_APP_BASE_URL"
    return
  fi

  printf 'http://%s\n' "$(review_app_gateway_address)"
}

review_app_environment_url() {
  printf '%s%s/\n' "$(review_app_base_url)" "$(review_app_base_path)"
}

review_app_registry_port() {
  printf '%s\n' "${REVIEW_APP_REGISTRY_PORT:-32000}"
}

review_app_image_registry() {
  if [ -n "${REVIEW_APP_IMAGE_REGISTRY:-}" ]; then
    printf '%s\n' "$REVIEW_APP_IMAGE_REGISTRY"
    return
  fi

  printf '%s:%s\n' "$(review_app_gateway_address)" "$(review_app_registry_port)"
}

review_app_image_repository() {
  if [ -n "${REVIEW_APP_IMAGE_REPOSITORY:-}" ]; then
    printf '%s\n' "$REVIEW_APP_IMAGE_REPOSITORY"
    return
  fi

  printf 'review-apps/%s\n' "$(review_app_project_path_slug)"
}

review_app_image_tag() {
  printf '%s\n' "${REVIEW_APP_IMAGE_TAG:-${CI_COMMIT_SHA:-local}}"
}

review_app_image() {
  if [ -n "${REVIEW_APP_IMAGE:-}" ]; then
    printf '%s\n' "$REVIEW_APP_IMAGE"
    return
  fi

  printf '%s/%s:%s\n' \
    "$(review_app_image_registry)" \
    "$(review_app_image_repository)" \
    "$(review_app_image_tag)"
}

review_app_registry_namespace() {
  printf '%s\n' "${REVIEW_APP_REGISTRY_NAMESPACE:-container-registry}"
}

review_app_registry_service_name() {
  printf '%s\n' "${REVIEW_APP_REGISTRY_SERVICE_NAME:-registry}"
}

review_app_bootstrap_env_file() {
  printf '%s\n' "${REVIEW_APP_BOOTSTRAP_ENV_FILE:-review-app-bootstrap.env}"
}

review_app_gitlab_env_file() {
  printf '%s\n' "${REVIEW_APP_GITLAB_ENV_FILE:-review-app.env}"
}

review_app_data_source() {
  printf '%s\n' "${REVIEW_APP_DATA_SOURCE:-butler}"
}

review_app_shared_fixture_root() {
  printf '%s\n' "${REVIEW_APP_SHARED_FIXTURE_ROOT:-/var/tmp/fov-quicklook-review-app-fixtures}"
}

review_app_shared_fixture_path() {
  printf '%s/%s\n' \
    "$(review_app_shared_fixture_root)" \
    "$(review_app_project_path_slug)"
}

review_app_dummy_visit_count() {
  printf '%s\n' "${REVIEW_APP_DUMMY_VISIT_COUNT:-50}"
}

review_app_butler_visit_count() {
  printf '%s\n' "${REVIEW_APP_BUTLER_VISIT_COUNT:-2000}"
}

review_app_fixture_env_file() {
  case "$(review_app_data_source)" in
    dummy)
      printf '%s/dummy.env\n' "$(review_app_shared_fixture_path)"
      ;;
    butler)
      printf '%s/butler.env\n' "$(review_app_shared_fixture_path)"
      ;;
    *)
      echo "unsupported REVIEW_APP_DATA_SOURCE: $(review_app_data_source)" >&2
      exit 1
      ;;
  esac
}

review_app_repository_name() {
  case "$(review_app_data_source)" in
    dummy)
      printf 'dummy\n'
      ;;
    butler)
      printf '%s\n' "${REVIEW_APP_FIXTURE_REPOSITORY_NAME:-reviewapp-ci}"
      ;;
  esac
}

review_app_sample_exposure_id() {
  printf '%s\n' "${REVIEW_APP_SAMPLE_EXPOSURE_ID:-910001}"
}

review_app_sample_visit_name() {
  printf '%s:raw:%s\n' "$(review_app_repository_name)" "$(review_app_sample_exposure_id)"
}

review_app_generator_replicas() {
  printf '%s\n' "${REVIEW_APP_GENERATOR_REPLICAS:-2}"
}
