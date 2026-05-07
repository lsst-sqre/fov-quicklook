#!/bin/sh

set -eu

ip=$(
  kubectl get nodes \
    -o jsonpath='{range .items[*]}{range .status.addresses[?(@.type=="InternalIP")]}{.address}{"\n"}{end}{end}' |
    awk 'NF { print; exit }'
)

if [ -z "$ip" ]; then
  echo "failed to detect Kubernetes node InternalIP" >&2
  exit 1
fi

printf '%s\n' "$ip"
