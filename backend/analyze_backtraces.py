#!/usr/bin/env python3
# バックトレース分析スクリプト

from pathlib import Path
from collections import defaultdict

results_dir = Path('backtrace_results')

# スレッド情報の抽出
waiting_threads = defaultdict(list)

for log_file in sorted(results_dir.glob('*.log')):
    pid = log_file.stem.split('_')[1]
    content = log_file.read_text()
    
    # キー関数を探す
    if 'generate_single_fits_tiles_pipeline' in content:
        waiting_threads['Manager_create'].append(pid)
    if 'serve_forever' in content:
        waiting_threads['serve_forever'].append(pid)
    if 'ProcessPoolExecutor' in content or '_start_executor' in content:
        waiting_threads['ProcessPoolExecutor'].append(pid)
    if 'Event.wait' in content or 'queue.get' in content or 'threading.wait' in content:
        if '_recv' in content:
            waiting_threads['IPC_recv'].append(pid)
        else:
            waiting_threads['threading_wait'].append(pid)

print("=== デッドロック状態の分析 ===\n")
for category, pids in sorted(waiting_threads.items()):
    print(f"{category}: {len(pids)} プロセス")
    print(f"  PID: {', '.join(pids[:5])}{'...' if len(pids) > 5 else ''}\n")

# メインプロセスを詳細分析
main_log = results_dir / 'backtrace_2968184.log'
print("=== メインプロセス (2968184) のクリティカルスレッド分析 ===")
main_content = main_log.read_text()

# Current thread を探す
if 'Current thread' in main_content:
    lines = main_content.split('\n')
    for i, line in enumerate(lines):
        if 'Current thread 0x00007bfb7327b740' in line:
            print(f"\n{line}")
            # generate_single_fits_tiles_pipeline を探す
            for j in range(i+1, min(i+100, len(lines))):
                if 'generate_single_fits_tiles_pipeline' in lines[j]:
                    print("\n*** FOUND: generate_single_fits_tiles_pipeline at line", j, "***")
                    # 周辺を表示
                    for k in range(max(0, j-5), min(j+15, len(lines))):
                        print(lines[k])
                    break
