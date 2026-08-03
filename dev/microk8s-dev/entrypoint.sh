#!/bin/sh

set -eu

mkdir -p /root/.config/fish/functions /root/.local/share/fish /root/.cache/fish
env | grep -E '^(QUICKLOOK_|VITE_|FQ_|KUBERNETES_)' > /root/.env || :

exec sleep infinity
