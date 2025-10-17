#!/bin/bash

# バックトレース取得スクリプト
# 子孫プロセスから順に SIGUSR1 を送信

cd /home/michitaro/fov-quicklook2/backend

# logファイルの現在のサイズを記録
get_log_size() {
    stat -c%s ./log 2>/dev/null || echo 0
}

# pid毎にバックトレースを取得
pids=(
    # 最もネストが深いプロセスから順に
    2968449 2968458 2968549 2968553 2968658
    2968204 2968438 2968441 2968543 2968571
    2968213 2968430 2968457 2968534 2968537 2968540 2968547 2968550
    2968459 2968473 2968485 2968496 2968505 2968518 2968526 2968531
    2968203 2968230
    2968212 2968235 2968245 2968251 2968257 2968263 2968269 2968275 2968281
    2968287 2968293 2968299 2968305 2968311 2968317 2968323 2968329 2968335
    2968341 2968347 2968353 2968359 2968365 2968371 2968377 2968383 2968389
    2968395 2968400 2968405 2968411 2968417
    2968420 2968421 2968433 2968436
    2968184
)

for pid in "${pids[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
        echo "=== Sending SIGUSR1 to PID $pid ==="
        old_size=$(get_log_size)
        kill -SIGUSR1 "$pid"
        sleep 0.5
        new_size=$(get_log_size)
        if [ "$new_size" -gt "$old_size" ]; then
            echo "✓ Backtrace written for PID $pid"
            # バックトレースを個別ファイルに抽出
            tail -n +1 ./log | sed -n "/$pid/,/^$/p" > "backtrace_pid_${pid}.txt" 2>/dev/null || true
        else
            echo "✗ No backtrace for PID $pid"
        fi
    else
        echo "✗ PID $pid not found"
    fi
    sleep 0.2
done

echo "=== Backtrace collection complete ==="
echo "Final log size: $(get_log_size) bytes"
