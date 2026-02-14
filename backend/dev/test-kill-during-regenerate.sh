#!/usr/bin/env bash
#
# regenerate中にkill_random_generatorを実行するテスト
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook"
TOKEN_FILE="$SCRIPT_DIR/.gafaelfawr-token"
PYTHON="${SCRIPT_DIR}/../.venv/bin/python"

VISIT="${1:-embargo:raw:2026012800342}"
KILL_DELAY="${2:-5}"

get_token() {
    cat "$TOKEN_FILE"
}

TOKEN="$(get_token)"

echo "=== kill_random_generator テスト ==="
echo "Visit: $VISIT"
echo "Kill delay: ${KILL_DELAY}s"
echo ""

# 1. キャッシュ削除
echo "--- キャッシュ削除 ---"
curl -s -X DELETE -H "Cookie: gafaelfawr=\"${TOKEN}\"" "${BASE_URL}/api/quicklooks/${VISIT}" > /dev/null
echo "✓ キャッシュ削除完了"

# 2. regenerateをバックグラウンドで開始
echo ""
echo "--- regenerate開始 ---"
curl -s -X POST -H "Cookie: gafaelfawr=\"${TOKEN}\"" -H "Content-Type: application/json" \
    "${BASE_URL}/api/quicklooks" -d "{\"visit\": \"${VISIT}\"}" > /dev/null

START_TIME=$(date +%s)

# 3. kill_random_generatorをKILL_DELAY秒後に実行
(
    sleep "$KILL_DELAY"
    echo ""
    echo "--- kill_random_generator 実行 (${KILL_DELAY}s後) ---"
    KILL_RESULT=$(curl -s -X POST -H "Cookie: gafaelfawr=\"${TOKEN}\"" \
        "${BASE_URL}/api/admin/kill_random_generator")
    echo "kill結果: $KILL_RESULT"
) &
KILL_PID=$!

# 4. WebSocketで進捗を監視（タイムアウト180秒）
echo "WebSocket で進捗を監視中..."
$PYTHON -c "
import asyncio
import json
import sys
import time

visit = '${VISIT}'
start = ${START_TIME}
timeout = 180

async def monitor():
    try:
        import websockets
    except ImportError:
        print('websocketsライブラリが必要です: pip install websockets', file=sys.stderr)
        sys.exit(1)

    uri = '$(echo "${BASE_URL}" | sed 's|^https://|wss://|')/api/quicklooks/*/status.ws'
    headers = {'Cookie': 'gafaelfawr=\"${TOKEN}\"'}
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

                if elapsed > timeout:
                    print(f'\n\n✗ タイムアウト ({timeout}秒)')
                    sys.exit(1)

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
"
RESULT=$?

wait $KILL_PID 2>/dev/null || true

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "経過時間: ${ELAPSED}秒"

if [ $RESULT -eq 0 ]; then
    echo "✓ テスト成功: kill_random_generator後もregenerate完了"
else
    echo "✗ テスト失敗: exit code=$RESULT"
fi

exit $RESULT
