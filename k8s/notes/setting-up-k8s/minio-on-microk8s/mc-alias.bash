#!/usr/bin/env bash
set -Eeuo pipefail

# ==== デフォルト値（必要に応じて引数で上書き）====
TENANT="microk8s"            # テナント名
NAMESPACE="minio-operator"   # Namespace
SERVICE="minio"              # S3 API の Service 名（通常は minio）
ALIAS=""                     # mc のエイリアス名（未指定なら TENANT を使用）
MODE="internal"              # internal|nodeport|url
HOST=""                      # MODE=nodeport 時の Node のIP/DNS
SCHEME=""                    # http|https（未指定なら port=443 -> https、それ以外は http）
USE_SECONDARY="false"        # true で ${TENANT}-user-1 を使用
INSECURE="false"             # true で mc --insecure を付与（自己署名対策）
URL=""                       # MODE=url 時の完全な URL (例: http://s3.example.com:9000)

usage() {
  cat <<'USAGE'
Usage:
  setup_mc_alias.sh [options]

Options:
  -t, --tenant <name>        Tenant name (default: microk8s)
  -n, --namespace <ns>       Namespace (default: minio-operator)
      --service <name>       S3 Service name (default: minio)
  -a, --alias <alias>        mc alias 名 (default: tenant名)
      --mode <m>             internal | nodeport | url (default: internal)
      --host <host>          MODE=nodeport のとき必須 (例: 192.168.1.10)
      --scheme <http|https>  明示的にスキームを指定（未指定なら自動推測）
      --url <URL>            MODE=url のとき必須 (例: http://s3.example.com:9000)
      --secondary            ルートではなく ${TENANT}-user-1 の資格情報を使用
      --insecure             mc に --insecure を付ける（自己署名証明書など）
  -h, --help                 このヘルプを表示
USAGE
}

# ========== 引数パース ==========
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tenant) TENANT="$2"; shift 2 ;;
    -n|--namespace) NAMESPACE="$2"; shift 2 ;;
    --service) SERVICE="$2"; shift 2 ;;
    -a|--alias) ALIAS="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --scheme) SCHEME="$2"; shift 2 ;;
    --url) URL="$2"; MODE="url"; shift 2 ;;
    --secondary) USE_SECONDARY="true"; shift ;;
    --insecure) INSECURE="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

[[ -z "$ALIAS" ]] && ALIAS="$TENANT"

# ========== 依存コマンド確認 ==========
command -v microk8s >/dev/null || { echo "microk8s が見つかりません"; exit 1; }
command -v mc       >/dev/null || { echo "mc (MinIO Client) が見つかりません"; exit 1; }

K="microk8s kubectl -n ${NAMESPACE}"

# ========== 資格情報の取得 ==========
# 公式手順: ルート資格情報は ${TENANT}-env-configuration Secret の config.env に格納
# （base64 デコード後、MINIO_ROOT_USER / MINIO_ROOT_PASSWORD を利用）[1](https://microk8s.io/docs/addon-minio)
if [[ "$USE_SECONDARY" == "true" ]]; then
  ACCESS="$($K get secret ${TENANT}-user-1 -o jsonpath='{.data.CONSOLE_ACCESS_KEY}' | base64 -d)"
  SECRET="$($K get secret ${TENANT}-user-1 -o jsonpath='{.data.CONSOLE_SECRET_KEY}' | base64 -d)"
else
  # config.env を eval で取り込み（MINIO_ROOT_USER / MINIO_ROOT_PASSWORD を得る）
  eval "$($K get secret ${TENANT}-env-configuration -o jsonpath='{.data.config\.env}' | base64 -d)"
  ACCESS="${MINIO_ROOT_USER:-}"
  SECRET="${MINIO_ROOT_PASSWORD:-}"
fi

if [[ -z "${ACCESS:-}" || -z "${SECRET:-}" ]]; then
  echo "資格情報の取得に失敗しました。テナント名/Namespace を確認してください。"
  exit 1
fi

# ========== エンドポイントの決定 ==========
# 公式ドキュメント例: svc/minio から HOST と PORT を取得し mc alias set に渡す[1](https://microk8s.io/docs/addon-minio)
case "$MODE" in
  internal)
    HOST="$($K get svc ${SERVICE} -o jsonpath='{.spec.clusterIP}')"
    PORT="$($K get svc ${SERVICE} -o jsonpath='{.spec.ports[0].port}')"
    ;;
  nodeport)
    [[ -n "$HOST" ]] || { echo "--mode nodeport では --host <NodeのIP/DNS> が必須です"; exit 1; }
    PORT="$($K get svc ${SERVICE} -o jsonpath='{.spec.ports[0].nodePort}')"
    ;;
  url)
    [[ -n "$URL" ]] || { echo "--url <http(s)://host:port> を指定してください"; exit 1; }
    ;;
  *)
    echo "Unknown MODE: $MODE"; exit 1 ;;
esac

if [[ "${MODE}" != "url" ]]; then
  if [[ -z "$SCHEME" ]]; then
    if [[ "${PORT}" == "443" ]]; then SCHEME="https"; else SCHEME="http"; fi
  fi
  URL="${SCHEME}://${HOST}:${PORT}"
fi
# ========== mc alias set 実行 ==========
# mc alias set は 「URL / ACCESS_KEY / SECRET_KEY」を指定してエイリアスを登録します。[2](https://docs.min.io/community/minio-object-store/reference/minio-mc/mc-alias-set.html)
echo "==> mc alias set ${ALIAS} ${URL}"
MC_ARGS=()
if [[ "$INSECURE" == "true" ]]; then
  MC_ARGS+=(--insecure)  # 自己署名証明書での検証回避フラグ（必要時のみ）[3](https://github.com/minio/mc/issues/4024)
fi

mc alias set "${ALIAS}" "${URL}" "${ACCESS}" "${SECRET}" "${MC_ARGS[@]}"

echo "完了: 'mc ls ${ALIAS}' で接続確認できます。"
