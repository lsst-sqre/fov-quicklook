#!/usr/bin/env bash
#
# ArgoCD操作用ユーティリティスクリプト
#
# 使い方:
#   # 1. トークンの設定（ブラウザの「Copy as cURL」出力を使う）
#   ./argocd.sh extract-token "curl 'https://...' -H 'Cookie: argocd.token=eyJ...'"
#   # → .argocd-token ファイルにトークンが保存される
#
#   # 2. Deploymentの再起動
#   ./argocd.sh restart                    # coordinator, generator, frontend, debug を再起動
#   ./argocd.sh restart coordinator        # coordinator だけ再起動
#   ./argocd.sh restart generator frontend # 複数指定
#
#   # 3. 状態表示
#   ./argocd.sh status
#
#   # 4. Phalanxリポジトリの参照ブランチ管理
#   ./argocd.sh get-branch                                   # 現在のブランチを表示
#   ./argocd.sh set-branch fov-quicklook/add-main-repository # ブランチを変更
#   ./argocd.sh set-branch main --sync                       # ブランチを変更して即sync
#
#   # 5. ArgoCD sync（マニフェスト適用）
#   ./argocd.sh sync
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARGOCD_SERVER="usdf-rsp-dev.slac.stanford.edu"
ARGOCD_BASE="https://${ARGOCD_SERVER}/argo-cd"
APP_NAME="fov-quicklook"
APP_NAMESPACE="fov-quicklook"

DEFAULT_DEPLOYMENTS=(coordinator generator frontend debug)
ALL_DEPLOYMENTS=(coordinator generator frontend db debug)

# --- トークン管理 ---

get_token() {
    if [[ -n "${ARGOCD_TOKEN:-}" ]]; then
        echo "$ARGOCD_TOKEN"
        return
    fi

    local token_file="$SCRIPT_DIR/.argocd-token"
    if [[ -f "$token_file" ]]; then
        cat "$token_file"
        return
    fi

    echo "エラー: ArgoCD トークンが設定されていません。" >&2
    echo '  eval "$('"$0"' extract-token <curl-command>)"' >&2
    return 1
}

# --- Deployment名の正規化 ---

resolve_deployment_name() {
    local short_name="$1"
    case "$short_name" in
        coordinator|generator|frontend|db|debug)
            echo "fov-quicklook-${short_name}"
            ;;
        fov-quicklook-*)
            echo "$short_name"
            ;;
        *)
            echo "エラー: 不明なDeployment名: $short_name" >&2
            echo "利用可能: ${ALL_DEPLOYMENTS[*]}" >&2
            return 1
            ;;
    esac
}

# --- コマンド ---

cmd_restart() {
    local targets=("$@")
    if [[ ${#targets[@]} -eq 0 ]]; then
        targets=("${DEFAULT_DEPLOYMENTS[@]}")
    fi

    local token
    token="$(get_token)"

    for short_name in "${targets[@]}"; do
        local deployment
        deployment="$(resolve_deployment_name "$short_name")"
        echo -n "再起動中: $deployment ... "

        argocd app actions run "$APP_NAME" restart \
            --kind Deployment \
            --resource-name "$deployment" \
            --namespace "$APP_NAMESPACE" \
            --group apps \
            --server "$ARGOCD_SERVER" \
            --grpc-web \
            --grpc-web-root-path /argo-cd \
            --auth-token "$token"

        echo "✓"
    done
}

cmd_status() {
    local token
    token="$(get_token)"

    # REST API経由で取得（CLIの app get は project get 権限が必要なため）
    echo "=== fov-quicklook Deployment 状態 ==="
    for short_name in "${ALL_DEPLOYMENTS[@]}"; do
        local deployment
        deployment="$(resolve_deployment_name "$short_name")"

        local info
        info="$(curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/resource?namespace=${APP_NAMESPACE}&resourceName=${deployment}&version=v1&group=apps&kind=Deployment" \
            -H "Cookie: argocd.token=${token}" 2>/dev/null)" || {
            echo "  $deployment: 取得失敗"
            continue
        }

        local replicas ready image
        replicas="$(echo "$info" | python3 -c "import sys,json; m=json.load(sys.stdin); d=json.loads(m['manifest']); print(d['status'].get('replicas', '?'))" 2>/dev/null || echo '?')"
        ready="$(echo "$info" | python3 -c "import sys,json; m=json.load(sys.stdin); d=json.loads(m['manifest']); print(d['status'].get('readyReplicas', '0'))" 2>/dev/null || echo '?')"
        image="$(echo "$info" | python3 -c "import sys,json; m=json.load(sys.stdin); d=json.loads(m['manifest']); print(d['spec']['template']['spec']['containers'][0]['image'])" 2>/dev/null || echo '?')"

        echo "  $deployment: ${ready}/${replicas} ready  image=${image}"
    done
}

cmd_extract_token() {
    if [[ $# -eq 0 ]]; then
        echo "使い方: $0 extract-token <curl-command-string>" >&2
        echo "  Safariの 'Copy as cURL' 等で取得したcurlコマンドを引数に渡してください。" >&2
        return 1
    fi

    local token
    token="$(echo "$*" | grep -oP 'argocd\.token=\K[^;"\x27 ]+')" || {
        echo "エラー: curlコマンドからargocd.tokenを抽出できませんでした。" >&2
        return 1
    }

    echo -n "$token" > "$SCRIPT_DIR/.argocd-token"
    echo "トークンを ${SCRIPT_DIR}/.argocd-token に保存しました。" >&2
    echo "以降 argocd.sh のコマンドはこのファイルからトークンを読み込みます。" >&2
}

cmd_logs() {
    local component="${1:-coordinator}"
    local deployment
    deployment="$(resolve_deployment_name "$component")"

    local token
    token="$(get_token)"

    # Pod名を取得
    local pod_name
    pod_name="$(curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/resource-tree" \
        -H "Cookie: argocd.token=${token}" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
for n in data.get('nodes', []):
    if n['kind'] == 'Pod' and n.get('name', '').startswith('${deployment}-'):
        print(n['name'])
        break
" 2>/dev/null)" || {
        echo "エラー: ${deployment} のPodが見つかりません。" >&2
        return 1
    }

    if [[ -z "$pod_name" ]]; then
        echo "エラー: ${deployment} のPodが見つかりません。" >&2
        return 1
    fi

    echo "=== ログ: $pod_name ===" >&2

    # ログを取得して人間が読める形式で表示
    curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/logs?namespace=${APP_NAMESPACE}&podName=${pod_name}&container=${deployment}&sinceSeconds=600" \
        -H "Cookie: argocd.token=${token}" \
        | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        data = json.loads(line)
        print(data['result']['content'])
    except:
        pass
"
}

cmd_get_branch() {
    local token
    token="$(get_token)"

    local info
    info="$(curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}" \
        -H "Cookie: argocd.token=${token}")" || {
        echo "エラー: アプリケーション情報の取得に失敗しました。" >&2
        return 1
    }

    local revision repo_url path
    revision="$(echo "$info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['spec']['source']['targetRevision'])" 2>/dev/null)"
    repo_url="$(echo "$info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['spec']['source']['repoURL'])" 2>/dev/null)"
    path="$(echo "$info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['spec']['source']['path'])" 2>/dev/null)"

    echo "repo: ${repo_url}"
    echo "path: ${path}"
    echo "branch: ${revision}"
}

cmd_set_branch() {
    local branch=""
    local do_sync=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sync)
                do_sync=true
                shift
                ;;
            -*)
                echo "エラー: 不明なオプション: $1" >&2
                return 1
                ;;
            *)
                branch="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$branch" ]]; then
        echo "使い方: $0 set-branch <branch-name> [--sync]" >&2
        echo "  例: $0 set-branch main" >&2
        echo "  例: $0 set-branch fov-quicklook/add-main-repository --sync" >&2
        return 1
    fi

    local token
    token="$(get_token)"

    echo -n "ブランチを '${branch}' に変更中 ... "
    argocd app set "$APP_NAME" \
        --revision "$branch" \
        --server "$ARGOCD_SERVER" \
        --grpc-web \
        --grpc-web-root-path /argo-cd \
        --auth-token "$token"
    echo "✓"

    if [[ "$do_sync" == true ]]; then
        cmd_sync
    fi
}

cmd_sync() {
    local token
    token="$(get_token)"

    echo "ArgoCD sync を実行中 ..."
    argocd app sync "$APP_NAME" \
        --server "$ARGOCD_SERVER" \
        --grpc-web \
        --grpc-web-root-path /argo-cd \
        --auth-token "$token"
}

# --- メイン ---

usage() {
    echo "使い方: $0 <command> [args...]"
    echo ""
    echo "コマンド:"
    echo "  restart [deployment...]  Deploymentの再起動 (デフォルト: ${DEFAULT_DEPLOYMENTS[*]})"
    echo "  status                   Deploymentの状態表示"
    echo "  logs [deployment]        Podのログ表示 (デフォルト: coordinator)"
    echo "  get-branch               Phalanxリポジトリの参照ブランチを表示"
    echo "  set-branch <branch> [--sync]  参照ブランチを変更（--syncで即マニフェスト適用）"
    echo "  sync                     ArgoCD syncを実行"
    echo "  extract-token <curl>     curlコマンドからargocd.tokenを抽出して .argocd-token に保存"
    echo ""
    echo "Deployment名: ${ALL_DEPLOYMENTS[*]}"
    echo ""
    echo "トークン設定:"
    echo "  $0 extract-token \"<SafariのCopy as cURL出力>\""
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

command="$1"
shift

case "$command" in
    restart)
        cmd_restart "$@"
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$@"
        ;;
    get-branch)
        cmd_get_branch
        ;;
    set-branch)
        cmd_set_branch "$@"
        ;;
    sync)
        cmd_sync
        ;;
    extract-token)
        cmd_extract_token "$@"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "エラー: 不明なコマンド: $command" >&2
        usage
        exit 1
        ;;
esac
