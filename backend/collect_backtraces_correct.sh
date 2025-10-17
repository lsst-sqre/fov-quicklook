#!/bin/bash
# 正しい手順でバックトレースを取得

cd /home/michitaro/fov-quicklook2/backend

# 親プロセスから始める
pids=(
    2968184  # メインプロセス
    2968203 2968212 2968230  # 第1層子プロセス
    2968430  # ネストされたプロセス
    2968459 2968473 2968485 2968496 2968505 2968518 2968526 2968531  # 2968230 の子
    2968235 2968245 2968251 2968257 2968263 2968269 2968275 2968281
    2968287 2968293 2968299 2968305 2968311 2968317 2968323 2968329
    2968335 2968341 2968347 2968353 2968359 2968365 2968371 2968377
    2968383 2968389 2968395 2968400 2968405 2968411 2968417
    2968420 2968421 2968433 2968436
)

mkdir -p backtrace_results

for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
        echo "=== PID $pid: Sending SIGUSR1 ==="
        kill -SIGUSR1 "$pid"
        sleep 1
        
        # ログファイルの内容をコピー
        if [ -s ./log ]; then
            cp ./log "backtrace_results/backtrace_${pid}.log"
            echo "✓ Backtrace saved for PID $pid ($(wc -c < backtrace_results/backtrace_${pid}.log) bytes)"
        else
            echo "✗ No backtrace for PID $pid"
        fi
        
        # ログを truncate して次のプロセスの準備
        truncate -s 0 ./log
        sleep 0.5
    else
        echo "✗ PID $pid not found"
    fi
done

echo ""
echo "=== Collection Complete ==="
ls -lh backtrace_results/
