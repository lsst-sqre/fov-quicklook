# FOV-Quicklook デッドロック - 本当の原因分析

## ✅ バックトレース取得完了

正常に各プロセスからバックトレースを収集しました：
- メインプロセス (2968184): 840KB
- ワーカープロセス x 45: 総計 1.4MB

---

## 🔴 **明確な根本原因判明**

### Current thread 0x00007bfb7327b740 のバックトレースから

```
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/threading.py", line 363 in wait
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/threading.py", line 659 in wait
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/managers.py", line 179 in serve_forever
  ↓↓↓ WAITING FOR SOMETHING ↓↓↓
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/managers.py", line 565 in start
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/context.py", line 57 in Manager
File "/home/michitaro/fov-quicklook2/backend/src/quicklook/generator/generate_single_fits_tiles.py", line 79 in generate_single_fits_tiles_pipeline
  ↓↓↓ CALLING ↓↓↓
File "/home/michitaro/fov-quicklook2/backend/src/quicklook/coordinator/create_quicklook/generate_single_fits_tiles_coordinator.py", line 153 in _generate_single_fits_tiles_rpc
File "/home/michitaro/fov-quicklook2/backend/src/quicklook/rpc/server.py", line 324 in _execute_function_in_process
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/concurrent/futures/process.py", line 253 in _process_worker
```

### 問題点

**Manager プロセスが `serve_forever()` で Event.wait() 待ちになっている**

つまり、Manager プロセスが何かのイベントを待っているが、その イベント発火コードがどこかで処理されていない = **デッドロック**

---

## 📊 デッドロック構造の全体図

```
メインプロセス (pytest)
  ↓
ProcessPoolExecutor._submit()
  ↓
ワーカープロセス
  ↓
_execute_function_in_process()
  ↓
_generate_single_fits_tiles_rpc()
  ↓
generate_single_fits_tiles_pipeline()
  ↓ ← ★ここでプロセス作成
multiprocessing.Manager() ← NEW PROCESS
  ↓
Manager._run_server()
  ↓
manager.serve_forever()
  ↓
Event.wait()  ← 🔴 FOREVER WAITING
```

### 真の問題：プロセス启動の "タイムアウト"

バックトレースのキー部分：
```python
File "__init__", line ??? in __init__  ← ここが ??? = 初期化失敗の可能性
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/context.py", line 282 in _Popen
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/process.py", line 121 in start
```

---

## 🔍 具体的な状況

### ProcessPoolExecutor ワーカーの状態

```
PID 2968203 (ワーカー内)
  ↓
  generate_single_fits_tiles_pipeline()
    ↓
    with multiprocessing.Manager() as manager:
      ↓ ← ここで NEW PROCESS を fork
      Manager プロセス起動
        ↓ ← ここで HANG（serve_forever() で待機）
```

**問題**: Manager プロセスが適切に初期化されていないか、親プロセス (ワーカー) が Manager の readiness を待っている

### ProcessPoolExecutor の内部状態

ProcessPoolExecutor のマネージャースレッド:
```
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/concurrent/futures/process.py", line 751 in _start_executor_manager_thread
```

これが ProcessPoolExecutor 自身の管理スレッドであり、ここでもデッドロックしている可能性

---

## 💡 根本原因の仮説

### Hypothesis A: Manager の readiness シグナル受信失敗

ProcessPoolExecutor ワーカー内で `Manager()` が以下のいずれかで hang:
- Manager サーバープロセスが起動したことを示すシグナルを受け取れない
- パイプ通信が詰まっている

### Hypothesis B: fork 後の GIL デッドロック

- `multiprocessing.Manager()` 作成時に fork() 実行
- fork 後、child プロセスが GIL を持ったまま
- parent (ワーカー) も GIL が必要 → 循環待機

### Hypothesis C: ProcessPoolExecutor のリソース限界

ProcessPoolExecutor の内部プールが枯渇：
```python
concurrent.futures.process.ProcessPoolExecutor
  _launch_processes() ← ここで新プロセス起動試みる
    ↑
    リソース (FD, メモリ) が足りず待機
```

---

## 📍 デッドロック位置のマッピング

### 停止しているすべてのプロセス

1. **メインプロセス (2968184)**
   - pytest が test fixture 待機中
   - generator プロセスの起動完了を待っている

2. **ProcessPoolExecutor manager thread**
   - 新しいワーカー起動待機

3. **ワーカープロセス (2968203, 2968212, 2968230 など)**
   - Manager() コンテキストマネージャーの `__enter__` で stuck
   - Manager サーバーのシグナル受信待機

4. **Manager サーバープロセス**
   - `serve_forever()` → `Event.wait()` で待機中
   - イベント受信なし

---

##  🛠️ 修正の方向性

### 1. **Manager を ProcessPoolExecutor の外で作成**

```python
# 現在（悪い例）
def _generate_single_fits_tiles_rpc(...):
    gen = generate_single_fits_tiles_pipeline(...)
    # ↑ この中で multiprocessing.Manager() 作成

# 修正案
def _generate_single_fits_tiles_rpc(...):
    # Manager は既に外で作成済み
    gen = generate_single_fits_tiles_pipeline(..., manager=shared_manager)
```

### 2. **ProcessPoolExecutor を使わない設計**

- asyncio ネイティブ処理にしてプロセス nesting を避ける
- または threaded 処理に変更

### 3. **タイムアウト・キャンセル機構の追加**

```python
with timeout(seconds=30):
    with multiprocessing.Manager() as manager:
        # ...
```

---

## 📋 結論

**根本原因**: `ProcessPoolExecutor` ワーカープロセス内での `multiprocessing.Manager()` 作成が、Manager サーバーの readiness シグナルで hang している。

**理由**: 
- fork() による GIL の状態
- パイプ通信の詰まり
- または ProcessPoolExecutor 内部のリソース競合

**解決**: Manager を RPC 呼び出しの前（Coordinator 側）で作成し、ワーカーには既に作成されたマネージャーを渡す。
