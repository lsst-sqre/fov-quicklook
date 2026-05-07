#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "$script_dir/common.sh"

namespace=$(review_app_namespace)
gateway_namespace=$(review_app_gateway_namespace)
route_name=$(review_app_route_name)

kubectl -n "$gateway_namespace" delete httproute "$route_name" --ignore-not-found=true
kubectl delete namespace "$namespace" --ignore-not-found=true --wait=false
