#!/usr/bin/env bash
#
# fov-quicklookアプリケーションのデプロイ検証スクリプト
#
# 使い方:
#   # 1. gafaelfawrトークンの設定（ブラウザの「Copy as cURL」出力を使う）
#   ./verify-deploy.sh extract-token "curl 'https://...' -H 'Cookie: gafaelfawr=\"eyJ...\"'"
#   # → .gafaelfawr-token ファイルにトークンが保存される
#
#   # 2. 基本チェック
#   ./verify-deploy.sh healthz           # healthzエンドポイント
#   ./verify-deploy.sh frontend          # フロントエンド応答
#   ./verify-deploy.sh all               # 全基本チェック
#
#   # 3. API操作
#   ./verify-deploy.sh jobs              # ジョブ一覧
#   ./verify-deploy.sh cache             # キャッシュ一覧
#   ./verify-deploy.sh cache-delete <visit_name>  # 特定キャッシュ削除
#   ./verify-deploy.sh visits [data_type] [repository_name] [limit]
#                                        # visit一覧（デフォルト: raw embargo 10）
#   ./verify-deploy.sh regenerate <visit_name>  # quicklook再生成（進捗監視付き）
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BASE_URL="https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook"
TOKEN_FILE="$SCRIPT_DIR/.gafaelfawr-token"
PYTHON="${SCRIPT_DIR}/../.venv/bin/python"

# --- トークン管理 ---

get_token() {
    if [[ -n "${GAFAELFAWR_TOKEN:-}" ]]; then
        echo "$GAFAELFAWR_TOKEN"
        return
    fi

    if [[ -f "$TOKEN_FILE" ]]; then
        cat "$TOKEN_FILE"
        return
    fi

    echo "エラー: gafaelfawr トークンが設定されていません。" >&2
    echo "  $0 extract-token \"<ブラウザのCopy as cURL出力>\"" >&2
    return 1
}

cmd_extract_token() {
    if [[ $# -eq 0 ]]; then
        echo "使い方: $0 extract-token <curl-command-string>" >&2
        echo "  ブラウザの 'Copy as cURL' で取得したcurlコマンドを引数に渡してください。" >&2
        echo "  gafaelfawr cookieを含む任意のページのリクエストで構いません。" >&2
        return 1
    fi

    local token
    token="$(echo "$*" | grep -oP 'gafaelfawr="\K[^"]+' || echo "")"
    if [[ -z "$token" ]]; then
        token="$(echo "$*" | grep -oP 'gafaelfawr=\K[^;"\x27 ]+' || echo "")"
    fi

    if [[ -z "$token" ]]; then
        echo "エラー: curlコマンドからgafaelfawrトークンを抽出できませんでした。" >&2
        return 1
    fi

    echo -n "$token" > "$TOKEN_FILE"
    echo "トークンを ${TOKEN_FILE} に保存しました。" >&2
}

# --- ヘルパー ---

api_get() {
    local path="$1"
    local token
    token="$(get_token)" || return 1
    curl -s -H "Cookie: gafaelfawr=\"${token}\"" "${BASE_URL}${path}"
}

api_post() {
    local path="$1"
    shift
    local token
    token="$(get_token)" || return 1
    curl -s -H "Cookie: gafaelfawr=\"${token}\"" -H "Content-Type: application/json" -X POST "${BASE_URL}${path}" "$@"
}

api_delete() {
    local path="$1"
    local token
    token="$(get_token)" || return 1
    curl -s -H "Cookie: gafaelfawr=\"${token}\"" -X DELETE "${BASE_URL}${path}"
}

api_get_status() {
    local path="$1"
    local token
    token="$(get_token)" || return 1

    local body http_code
    body="$(curl -s -w '\n%{http_code}' -H "Cookie: gafaelfawr=\"${token}\"" "${BASE_URL}${path}")"
    http_code="$(echo "$body" | tail -1)"
    body="$(echo "$body" | sed '$d')"

    echo "$http_code"
    echo "$body"
}

# --- 基本チェック ---

cmd_healthz() {
    echo "=== healthz エンドポイント確認 ==="
    local url="/api/healthz"
    echo "GET ${BASE_URL}${url}"

    local result http_code body
    result="$(api_get_status "$url")"
    http_code="$(echo "$result" | head -1)"
    body="$(echo "$result" | tail -n +2)"

    if [[ "$http_code" == "200" ]]; then
        echo "✓ Status: $http_code"
        echo "$body" | $PYTHON -m json.tool 2>/dev/null || echo "$body"
    else
        echo "✗ Status: $http_code"
        echo "$body"
        return 1
    fi
}

cmd_frontend() {
    echo "=== フロントエンド確認 ==="
    local url="/"
    echo "GET ${BASE_URL}${url}"

    local token http_code
    token="$(get_token)" || return 1
    http_code="$(curl -s -o /dev/null -w '%{http_code}' -H "Cookie: gafaelfawr=\"${token}\"" "${BASE_URL}${url}")"

    if [[ "$http_code" == "200" ]]; then
        echo "✓ Status: $http_code (フロントエンド応答OK)"
    else
        echo "✗ Status: $http_code"
        return 1
    fi
}

cmd_all() {
    local failed=0

    cmd_healthz || failed=1
    echo ""
    cmd_frontend || failed=1

    echo ""
    if [[ "$failed" -eq 0 ]]; then
        echo "=== 全チェック通過 ✓ ==="
    else
        echo "=== 一部チェック失敗 ✗ ==="
        return 1
    fi
}

# --- API操作 ---

cmd_jobs() {
    echo "=== ジョブ一覧 ==="
    local body
    body="$(api_get "/api/quicklooks/*/status")" || return 1

    local count
    count="$(echo "$body" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "?")"

    if [[ "$count" == "0" ]]; then
        echo "アクティブなジョブはありません。"
    else
        echo "アクティブジョブ数: $count"
        echo "$body" | $PYTHON -m json.tool 2>/dev/null || echo "$body"
    fi
}

cmd_cache() {
    echo "=== キャッシュ一覧 ==="
    local body
    body="$(api_get "/api/cache_entries")" || return 1

    echo "$body" | $PYTHON -c "
import sys, json
entries = json.load(sys.stdin)
print(f'キャッシュエントリ数: {len(entries)}')
total = sum(e['disk_usage'] for e in entries)
print(f'合計サイズ: {total / 1e9:.1f} GB')
print()
print(f'{\"visit_name\":<50} {\"ready\":>5} {\"disk_usage\":>12} created_at')
print('-' * 100)
for e in entries:
    size_gb = e['disk_usage'] / 1e9
    print(f'{e[\"visit_name\"]:<50} {str(e[\"ready\"]):>5} {size_gb:>9.1f} GB  {e[\"created_at\"][:19]}')
" 2>/dev/null || echo "$body" | $PYTHON -m json.tool 2>/dev/null || echo "$body"
}

cmd_cache_delete() {
    if [[ $# -eq 0 ]]; then
        echo "使い方: $0 cache-delete <visit_name>" >&2
        echo "  例: $0 cache-delete embargo:raw:2026012800326" >&2
        return 1
    fi

    local visit_name="$1"
    echo "=== キャッシュ削除: $visit_name ==="
    api_delete "/api/cache_entries/${visit_name}" > /dev/null || return 1
    echo "✓ キャッシュを削除しました: $visit_name"
}

cmd_visits() {
    local data_type="${1:-raw}"
    local repository_name="${2:-embargo}"
    local limit="${3:-10}"

    echo "=== visit一覧 (${repository_name}:${data_type}, limit=${limit}) ==="
    local body
    body="$(api_get "/api/visits?data_type=${data_type}&repository_name=${repository_name}&limit=${limit}")" || return 1

    echo "$body" | $PYTHON -c "
import sys, json
visits = json.load(sys.stdin)
print(f'件数: {len(visits)}')
print()
print(f'{\"id\":<40} {\"day_obs\":>10} {\"filter\":>10} {\"exp_time\":>8} observation_type')
print('-' * 110)
for v in visits:
    print(f'{v[\"id\"]:<40} {v.get(\"day_obs\",\"?\"):>10} {v.get(\"physical_filter\",\"?\"):>10} {v.get(\"exposure_time\",\"?\"):>8} {v.get(\"observation_type\",\"?\")}')
" 2>/dev/null || echo "$body" | $PYTHON -m json.tool 2>/dev/null || echo "$body"
}

cmd_tile_profile() {
    if [[ $# -eq 0 ]]; then
        echo "使い方: $0 tile-profile <visit_name>" >&2
        echo "  例: $0 tile-profile embargo:raw:2026012800326" >&2
        return 1
    fi

    local visit_name="$1"
    echo "=== Tile Profile: $visit_name ==="
    local body
    body="$(api_get "/api/quicklooks/${visit_name}/tile_profile")" || return 1

    echo "$body" | $PYTHON -c "
import sys, json
profile = json.load(sys.stdin)
if profile is None:
    print('プロファイルが見つかりません（まだ生成されていないか、古いキャッシュです）')
    sys.exit(0)
print()
print(f'  generate_single_fits_tiles: {profile[\"generate_single_fits_tiles\"]:.1f}s')
print(f'  merge_tiles:                {profile[\"merge_tiles\"]:.1f}s')
print(f'  upload_to_object_storage:   {profile[\"upload_to_object_storage\"]:.1f}s')
print(f'  ────────────────────────────────')
print(f'  total:                      {profile[\"total\"]:.1f}s')
" 2>/dev/null || echo "$body" | $PYTHON -m json.tool 2>/dev/null || echo "$body"
}

cmd_regenerate() {
    if [[ $# -eq 0 ]]; then
        echo "使い方: $0 regenerate <visit_name>" >&2
        echo "  例: $0 regenerate embargo:raw:2026012800326" >&2
        echo "" >&2
        echo "  キャッシュに存在するvisitの場合は先に削除してください:" >&2
        echo "    $0 cache-delete embargo:raw:2026012800326" >&2
        echo "    $0 regenerate embargo:raw:2026012800326" >&2
        return 1
    fi

    local visit_name="$1"
    echo "=== quicklook再生成: $visit_name ==="

    local start_time
    start_time="$(date +%s)"

    echo "POST /api/quicklooks  {\"visit\": \"${visit_name}\"}"
    local result
    result="$(api_post "/api/quicklooks" -d "{\"visit\": \"${visit_name}\"}")"
    echo "レスポンス: $result"

    echo ""
    echo "WebSocket で進捗を監視中... (Ctrl+C で中断)"
    echo ""

    local token
    token="$(get_token)" || return 1

    local ws_url
    ws_url="$(echo "${BASE_URL}" | sed 's|^https://|wss://|; s|^http://|ws://|')/api/quicklooks/*/status.ws"

    $PYTHON -c "
import asyncio
import json
import sys
import time

visit = '${visit_name}'
start = ${start_time}

async def monitor():
    try:
        import websockets
    except ImportError:
        print('websocketsライブラリが必要です: pip install websockets', file=sys.stderr)
        sys.exit(1)

    uri = '${ws_url}'
    headers = {'Cookie': 'gafaelfawr=\"${token}\"'}
    prev_stage = None
    prev_line_len = 0

    try:
        async with websockets.connect(uri, additional_headers=headers, max_size=10*1024*1024) as ws:
            async for msg in ws:
                data = json.loads(msg)
                job = data.get(visit)
                if job is None:
                    continue

                stage = job.get('stage')
                elapsed = time.time() - start

                if stage != prev_stage:
                    if prev_line_len > 0:
                        print()
                    print(f'[{elapsed:6.1f}s] Stage: {stage}')
                    prev_stage = stage
                    prev_line_len = 0

                for key in ['generate_single_fits_tiles', 'merge_tiles', 'transfer_tiles']:
                    progress = job.get(key)
                    if progress:
                        done = sum(1 for v in progress.values() if v and v.get('done'))
                        total = len(progress)
                        if total > 0:
                            pct = done / total * 100
                            line = f'  {key}: {done}/{total} ({pct:.0f}%)'
                            sys.stdout.write(f'\r{line}' + ' ' * max(0, prev_line_len - len(line)))
                            sys.stdout.flush()
                            prev_line_len = len(line)

                if stage == 'ready':
                    elapsed = time.time() - start
                    print(f'\n\n✓ 完了! 生成時間: {elapsed:.1f}秒')
                    return
                elif stage == 'error':
                    error_msg = job.get('error_message', '不明なエラー')
                    print(f'\n\n✗ エラー: {error_msg}')
                    sys.exit(1)

    except KeyboardInterrupt:
        elapsed = time.time() - start
        print(f'\n\n中断されました (経過時間: {elapsed:.1f}秒)')
        sys.exit(130)
    except Exception as e:
        print(f'\nWebSocket接続エラー: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(monitor())
" || true

    local end_time elapsed
    end_time="$(date +%s)"
    elapsed="$((end_time - start_time))"
    echo ""
    echo "経過時間: ${elapsed}秒"
}

# --- メイン ---

usage() {
    echo "使い方: $0 <command> [args...]"
    echo ""
    echo "基本チェック:"
    echo "  extract-token <curl>         curlコマンドからgafaelfawrトークンを抽出して保存"
    echo "  healthz                      healthzエンドポイントの確認"
    echo "  frontend                     フロントエンドへのアクセス確認"
    echo "  all                          全基本チェック実行"
    echo ""
    echo "API操作:"
    echo "  jobs                         アクティブジョブ一覧"
    echo "  cache                        キャッシュ一覧"
    echo "  cache-delete <visit_name>    特定visitのキャッシュ削除"
    echo "  visits [data_type] [repository_name] [limit]"
    echo "                               visit一覧 (デフォルト: raw embargo 10)"
    echo "  regenerate <visit_name>      quicklook再生成 (進捗監視付き)"
    echo "  tile-profile <visit_name>    タイル生成プロファイル表示"
    echo ""
    echo "visit_nameの形式: {repository_name}:{data_type}:{exposure_id}"
    echo "  例: embargo:raw:2026012800326"
    echo ""
    echo "トークン設定:"
    echo "  $0 extract-token \"<ブラウザのCopy as cURL出力>\""
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

command="$1"
shift

case "$command" in
    extract-token)
        cmd_extract_token "$@"
        ;;
    healthz)
        cmd_healthz
        ;;
    frontend)
        cmd_frontend
        ;;
    all)
        cmd_all
        ;;
    jobs)
        cmd_jobs
        ;;
    cache)
        cmd_cache
        ;;
    cache-delete)
        cmd_cache_delete "$@"
        ;;
    visits)
        cmd_visits "$@"
        ;;
    regenerate)
        cmd_regenerate "$@"
        ;;
    tile-profile)
        cmd_tile_profile "$@"
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
