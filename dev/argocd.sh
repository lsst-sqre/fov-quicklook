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
#   ./argocd.sh set-branch u/michitaro/fov-quicklook-diffimage-20260311-0512 # ブランチを変更
#   ./argocd.sh set-branch main --sync                       # ブランチを変更して即sync
#
#   # 5. ArgoCD sync（マニフェスト適用）
#   ./argocd.sh sync
#
#   # 6. Phalanx への安全な push
#   ./argocd.sh install-phalanx-hook      # plain な git push もガードする pre-push hook をインストール
#   ./argocd.sh phalanx-check            # push 前の安全チェック
#   ./argocd.sh phalanx-push             # 確認付きで origin に push
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARGOCD_SERVER="usdf-rsp-dev.slac.stanford.edu"
ARGOCD_BASE="https://${ARGOCD_SERVER}/argo-cd"
APP_NAME="fov-quicklook"
APP_NAMESPACE="fov-quicklook"
EXPECTED_APP_SOURCE_PATH="applications/fov-quicklook"
PHALANX_DIR="${SCRIPT_DIR}/../k8s/phalanx"
ZERO_OID="0000000000000000000000000000000000000000"
ARGOCD_TIMEOUT_SECONDS="${QUICKLOOK_ARGOCD_TIMEOUT_SECONDS:-120}"
ARGOCD_CONNECT_TIMEOUT_SECONDS="${QUICKLOOK_ARGOCD_CONNECT_TIMEOUT_SECONDS:-15}"

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

run_argocd_cli() {
    timeout "$ARGOCD_TIMEOUT_SECONDS" argocd "$@"
}

run_argocd_curl() {
    curl \
        --connect-timeout "$ARGOCD_CONNECT_TIMEOUT_SECONDS" \
        --max-time "$ARGOCD_TIMEOUT_SECONDS" \
        "$@"
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

is_expected_phalanx_repo_url() {
    local repo_url="$1"
    case "$repo_url" in
        https://github.com/lsst-sqre/phalanx|https://github.com/lsst-sqre/phalanx.git|git@github.com:lsst-sqre/phalanx|git@github.com:lsst-sqre/phalanx.git|ssh://git@github.com/lsst-sqre/phalanx|ssh://git@github.com/lsst-sqre/phalanx.git)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

ensure_phalanx_repo() {
    if ! git -C "$PHALANX_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "エラー: ${PHALANX_DIR} に Phalanx リポジトリが見つかりません。" >&2
        echo "  k8s/phalanx を clone してから再実行してください。" >&2
        return 1
    fi
}

validate_phalanx_remote() {
    local remote_name="${1:-origin}"
    local remote_url
    remote_url="$(git -C "$PHALANX_DIR" remote get-url "$remote_name" 2>/dev/null || true)"

    if [[ -z "$remote_url" ]]; then
        echo "エラー: Phalanx リポジトリに remote '${remote_name}' がありません。" >&2
        return 1
    fi

    if ! is_expected_phalanx_repo_url "$remote_url"; then
        echo "エラー: Phalanx remote '${remote_name}' が想定外です: ${remote_url}" >&2
        echo "  lsst-sqre/phalanx を push するつもりでなければ危険なので停止します。" >&2
        return 1
    fi
}

validate_argocd_branch_name() {
    local branch="$1"

    if [[ "${QUICKLOOK_ARGOCD_ALLOW_ANY_BRANCH:-}" == "1" ]]; then
        return 0
    fi

    case "$branch" in
        main|u/michitaro/fov-quicklook-*)
            return 0
            ;;
        *)
            echo "エラー: 想定外の Phalanx ブランチ名です: ${branch}" >&2
            echo "  許可: main または u/michitaro/fov-quicklook-*" >&2
            echo "  一時的に許可する場合は QUICKLOOK_ARGOCD_ALLOW_ANY_BRANCH=1 を指定してください。" >&2
            return 1
            ;;
    esac
}

validate_phalanx_push_branch_name() {
    local branch="$1"

    if [[ "${QUICKLOOK_ALLOW_UNSAFE_PUSH:-}" == "1" ]]; then
        return 0
    fi

    case "$branch" in
        u/michitaro/fov-quicklook-*)
            return 0
            ;;
        *)
            echo "エラー: 安全 push の対象外ブランチです: ${branch}" >&2
            echo "  許可: u/michitaro/fov-quicklook-*" >&2
            echo "  main や他用途の branch へ push したい場合は通常の git push を使うか、QUICKLOOK_ALLOW_UNSAFE_PUSH=1 を指定してください。" >&2
            return 1
            ;;
    esac
}

is_allowed_phalanx_path() {
    local path="$1"
    case "$path" in
        applications/fov-quicklook/*|docs/applications/fov-quicklook/*|environments/templates/applications/rsp/fov-quicklook.yaml)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

append_unique() {
    local -n items_ref="$1"
    local value="$2"
    local existing

    for existing in "${items_ref[@]:-}"; do
        if [[ "$existing" == "$value" ]]; then
            return 0
        fi
    done

    items_ref+=("$value")
}

collect_worktree_files() {
    local -n files_ref="$1"
    mapfile -t files_ref < <(
        {
            git -C "$PHALANX_DIR" diff --name-only --diff-filter=ACMR
            git -C "$PHALANX_DIR" diff --name-only --cached --diff-filter=ACMR
            git -C "$PHALANX_DIR" ls-files --others --exclude-standard
        } | awk 'NF' | sort -u
    )
}

collect_pending_push_files() {
    local -n files_ref="$1"

    if git -C "$PHALANX_DIR" rev-parse --verify --quiet '@{upstream}' >/dev/null 2>&1; then
        mapfile -t files_ref < <(git -C "$PHALANX_DIR" diff --name-only --diff-filter=ACMR '@{upstream}..HEAD')
        return
    fi

    if git -C "$PHALANX_DIR" rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
        local merge_base
        merge_base="$(git -C "$PHALANX_DIR" merge-base HEAD origin/main)"
        mapfile -t files_ref < <(git -C "$PHALANX_DIR" diff --name-only --diff-filter=ACMR "${merge_base}..HEAD")
        return
    fi

    mapfile -t files_ref < <(git -C "$PHALANX_DIR" show --pretty='' --name-only --diff-filter=ACMR HEAD | awk 'NF' | sort -u)
}

collect_push_range_files() {
    local local_oid="$1"
    local remote_oid="$2"
    local -n files_ref="$3"

    if [[ "$remote_oid" == "$ZERO_OID" ]]; then
        if git -C "$PHALANX_DIR" rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
            local merge_base
            merge_base="$(git -C "$PHALANX_DIR" merge-base "$local_oid" origin/main)"
            mapfile -t files_ref < <(git -C "$PHALANX_DIR" diff --name-only --diff-filter=ACMR "${merge_base}..${local_oid}")
            return
        fi

        mapfile -t files_ref < <(git -C "$PHALANX_DIR" show --pretty='' --name-only --diff-filter=ACMR "$local_oid" | awk 'NF' | sort -u)
        return
    fi

    mapfile -t files_ref < <(git -C "$PHALANX_DIR" diff --name-only --diff-filter=ACMR "${remote_oid}..${local_oid}")
}

report_file_safety() {
    local label="$1"
    shift
    local files=("$@")
    local path

    if [[ ${#files[@]} -eq 0 ]]; then
        echo "${label}: なし"
        return
    fi

    echo "${label}:"
    for path in "${files[@]}"; do
        if is_allowed_phalanx_path "$path"; then
            echo "  OK  ${path}"
        else
            echo "  NG  ${path}"
        fi
    done
}

collect_unsafe_files() {
    local -n result_ref="$1"
    shift
    local files=("$@")
    local path

    for path in "${files[@]}"; do
        if ! is_allowed_phalanx_path "$path"; then
            append_unique result_ref "$path"
        fi
    done
}

get_argocd_app_info() {
    local token
    token="$(get_token)"

    run_argocd_curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}" \
        -H "Cookie: argocd.token=${token}"
}

validate_argocd_app_source() {
    local app_info="$1"
    local repo_url path
    repo_url="$(echo "$app_info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['spec']['source']['repoURL'])" 2>/dev/null)"
    path="$(echo "$app_info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['spec']['source']['path'])" 2>/dev/null)"

    if ! is_expected_phalanx_repo_url "$repo_url"; then
        echo "エラー: ArgoCD の repoURL が想定外です: ${repo_url}" >&2
        return 1
    fi

    if [[ "$path" != "$EXPECTED_APP_SOURCE_PATH" ]]; then
        echo "エラー: ArgoCD の source.path が想定外です: ${path}" >&2
        echo "  想定: ${EXPECTED_APP_SOURCE_PATH}" >&2
        return 1
    fi
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

        run_argocd_cli app actions run "$APP_NAME" restart \
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
        info="$(run_argocd_curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/resource?namespace=${APP_NAMESPACE}&resourceName=${deployment}&version=v1&group=apps&kind=Deployment" \
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
    pod_name="$(run_argocd_curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/resource-tree" \
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
    run_argocd_curl -sf "${ARGOCD_BASE}/api/v1/applications/${APP_NAME}/logs?namespace=${APP_NAMESPACE}&podName=${pod_name}&container=${deployment}&sinceSeconds=600" \
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
    local info
    info="$(get_argocd_app_info)" || {
        echo "エラー: アプリケーション情報の取得に失敗しました。" >&2
        return 1
    }

    validate_argocd_app_source "$info"

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
        echo "  例: $0 set-branch u/michitaro/fov-quicklook-diffimage-20260311-0512 --sync" >&2
        return 1
    fi

    validate_argocd_branch_name "$branch"

    local token
    token="$(get_token)"

    local info
    info="$(get_argocd_app_info)" || {
        echo "エラー: アプリケーション情報の取得に失敗しました。" >&2
        return 1
    }

    validate_argocd_app_source "$info"

    echo -n "ブランチを '${branch}' に変更中 ... "
    run_argocd_cli app set "$APP_NAME" \
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

    local info
    info="$(get_argocd_app_info)" || {
        echo "エラー: アプリケーション情報の取得に失敗しました。" >&2
        return 1
    }

    validate_argocd_app_source "$info"

    echo "ArgoCD sync を実行中 ..."
    run_argocd_cli app sync "$APP_NAME" \
        --server "$ARGOCD_SERVER" \
        --grpc-web \
        --grpc-web-root-path /argo-cd \
        --auth-token "$token"
}

cmd_phalanx_check() {
    ensure_phalanx_repo
    validate_phalanx_remote origin

    local branch remote_url
    branch="$(git -C "$PHALANX_DIR" branch --show-current)"
    remote_url="$(git -C "$PHALANX_DIR" remote get-url origin)"

    echo "repo: ${PHALANX_DIR}"
    echo "remote: ${remote_url}"
    echo "branch: ${branch}"

    validate_phalanx_push_branch_name "$branch"

    local -a worktree_files=()
    local -a push_files=()
    local -a unsafe_files=()

    collect_worktree_files worktree_files
    collect_pending_push_files push_files

    report_file_safety "ローカル変更" "${worktree_files[@]}"
    report_file_safety "push対象差分" "${push_files[@]}"

    collect_unsafe_files unsafe_files "${worktree_files[@]}"
    collect_unsafe_files unsafe_files "${push_files[@]}"

    if [[ ${#unsafe_files[@]} -gt 0 ]]; then
        echo "エラー: fov-quicklook 関連以外の変更が含まれています。" >&2
        echo "  許可: applications/fov-quicklook/, docs/applications/fov-quicklook/, environments/templates/applications/rsp/fov-quicklook.yaml" >&2
        return 1
    fi

    echo "安全チェック OK"
}

cmd_phalanx_push() {
    ensure_phalanx_repo
    validate_phalanx_remote origin

    local assume_yes=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --yes)
                assume_yes=true
                shift
                ;;
            *)
                echo "エラー: 不明なオプション: $1" >&2
                echo "使い方: $0 phalanx-push [--yes]" >&2
                return 1
                ;;
        esac
    done

    local branch
    branch="$(git -C "$PHALANX_DIR" branch --show-current)"
    validate_phalanx_push_branch_name "$branch"

    local -a worktree_files=()
    local -a push_files=()
    collect_worktree_files worktree_files
    collect_pending_push_files push_files

    if [[ ${#worktree_files[@]} -gt 0 ]]; then
        echo "エラー: 未コミット変更があるため安全 push を停止します。" >&2
        report_file_safety "ローカル変更" "${worktree_files[@]}"
        echo "  commit/stash 後に再実行してください。" >&2
        return 1
    fi

    if [[ ${#push_files[@]} -eq 0 ]]; then
        echo "push 対象の差分がありません。" >&2
        return 1
    fi

    cmd_phalanx_check >/dev/null
    report_file_safety "push対象差分" "${push_files[@]}"

    if [[ "$assume_yes" != true ]]; then
        if [[ ! -t 0 ]]; then
            echo "エラー: 非対話環境では --yes が必要です。" >&2
            return 1
        fi

        local answer
        echo "push 先: origin/${branch}"
        read -r -p "続行するには branch 名 '${branch}' を入力してください: " answer
        if [[ "$answer" != "$branch" ]]; then
            echo "エラー: 入力が一致しなかったため push を中止しました。" >&2
            return 1
        fi
    fi

    # phalanx-push 自体が安全チェック済みなので、古い local hook に巻き込まれないよう hooks は使わない。
    git -C "$PHALANX_DIR" -c core.hooksPath=/dev/null push origin HEAD
}

cmd_install_phalanx_hook() {
    ensure_phalanx_repo

    local force=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force)
                force=true
                shift
                ;;
            *)
                echo "エラー: 不明なオプション: $1" >&2
                echo "使い方: $0 install-phalanx-hook [--force]" >&2
                return 1
                ;;
        esac
    done

    local hook_path="${PHALANX_DIR}/.git/hooks/pre-push"
    local marker="# fov-quicklook managed pre-push hook"

    if [[ -f "$hook_path" ]] && ! grep -Fq "$marker" "$hook_path"; then
        if [[ "$force" != true ]]; then
            echo "エラー: ${hook_path} に既存の pre-push hook があります。" >&2
            echo "  内容を確認してから --force を指定してください。" >&2
            return 1
        fi
    fi

    cat > "$hook_path" <<EOF
#!/usr/bin/env bash
${marker}
set -euo pipefail
exec "${SCRIPT_DIR}/argocd.sh" phalanx-pre-push-hook "\$@"
EOF
    chmod +x "$hook_path"

    echo "pre-push hook をインストールしました: ${hook_path}"
    echo "以後は plain な git push でも fov-quicklook 以外の差分があると停止します。"
}

cmd_phalanx_pre_push_hook() {
    if [[ "${QUICKLOOK_ALLOW_UNSAFE_PUSH:-}" == "1" ]]; then
        echo "警告: QUICKLOOK_ALLOW_UNSAFE_PUSH=1 のため pre-push ガードをスキップします。" >&2
        return 0
    fi

    ensure_phalanx_repo

    local remote_name="${1:-origin}"
    local remote_url="${2:-}"

    if [[ -n "$remote_url" ]] && ! is_expected_phalanx_repo_url "$remote_url"; then
        echo "エラー: 想定外の push 先です: ${remote_url}" >&2
        return 1
    fi

    validate_phalanx_remote "$remote_name"

    local -a unsafe_files=()
    local seen_update=false
    local local_ref local_oid remote_ref remote_oid
    while read -r local_ref local_oid remote_ref remote_oid; do
        [[ -z "${local_ref:-}" ]] && continue
        seen_update=true

        if [[ "$local_oid" == "$ZERO_OID" ]]; then
            echo "エラー: branch 削除は安全 push の対象外です。" >&2
            return 1
        fi

        case "$remote_ref" in
            refs/heads/*)
                ;;
            *)
                echo "エラー: branch push 以外は安全 push の対象外です: ${remote_ref}" >&2
                return 1
                ;;
        esac

        local remote_branch
        remote_branch="${remote_ref#refs/heads/}"
        validate_phalanx_push_branch_name "$remote_branch"

        local -a range_files=()
        collect_push_range_files "$local_oid" "$remote_oid" range_files
        collect_unsafe_files unsafe_files "${range_files[@]}"
    done

    if [[ "$seen_update" != true ]]; then
        return 0
    fi

    if [[ ${#unsafe_files[@]} -gt 0 ]]; then
        echo "エラー: pre-push ガードにより push を停止しました。" >&2
        echo "  fov-quicklook 関連以外のファイルが含まれています:" >&2
        local path
        for path in "${unsafe_files[@]}"; do
            echo "    ${path}" >&2
        done
        echo "  許可: applications/fov-quicklook/, docs/applications/fov-quicklook/, environments/templates/applications/rsp/fov-quicklook.yaml" >&2
        return 1
    fi
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
    echo "  phalanx-check            Phalanx の変更範囲を安全チェック"
    echo "  phalanx-push [--yes]     確認付きで Phalanx branch を origin に push"
    echo "  install-phalanx-hook [--force]  plain な git push も止める pre-push hook をインストール"
    echo "  extract-token <curl>     curlコマンドからargocd.tokenを抽出して .argocd-token に保存"
    echo ""
    echo "Deployment名: ${ALL_DEPLOYMENTS[*]}"
    echo ""
    echo "トークン設定:"
    echo "  $0 extract-token \"<SafariのCopy as cURL出力>\""
    echo ""
    echo "Phalanx 安全運用:"
    echo "  $0 install-phalanx-hook"
    echo "  $0 phalanx-check"
    echo "  $0 phalanx-push"
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
    phalanx-check)
        cmd_phalanx_check "$@"
        ;;
    phalanx-push)
        cmd_phalanx_push "$@"
        ;;
    install-phalanx-hook)
        cmd_install_phalanx_hook "$@"
        ;;
    phalanx-pre-push-hook)
        cmd_phalanx_pre_push_hook "$@"
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
