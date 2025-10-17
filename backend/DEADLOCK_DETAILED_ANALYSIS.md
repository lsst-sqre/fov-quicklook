# デッドロック調査 - 詳細分析と修正策

## 調査実施内容

```bash
# プロセスツリー記録
pstree -p 2968184 > backtrace_pstree.txt

# ログ truncate
truncate -s 0 ./log

# SIGUSR1 シグナル送信でバックトレース取得
bash collect_backtraces.sh
```

## 結果

- **プロセス数**: 51個のプロセスがハング状態
- **ログサイズ**: 849,631 バイト (6,525 行)
- **バックトレース**: 複数プロセスからの同一パターンの積み重ね

---

## デッドロックメカニズム

### 呼び出しチェーン

```
pytest main (2968184)
├─ concurrent.futures.ProcessPoolExecutor (5 workers)
│  ├─ Worker 1 (2968203)
│  │  ├─ _execute_function_in_process
│  │  │  └─ _generate_single_fits_tiles_rpc
│  │  │     └─ generate_single_fits_tiles_pipeline ★ PROBLEM HERE
│  │  │        ├─ multiprocessing.Manager()  ← 新プロセス起動
│  │  │        │  └─ Manager server process
│  │  │        └─ multiprocessing.Pool(8)   ← さらに8プロセス起動
│  │  │           └─ 8個のワーカープロセス
```

### デッドロック条件

1. **リソース競合**:
   - ProcessPoolExecutor のワーカー5個
   - 各ワーカー内で Manager (1) + Pool (8) = 9プロセス
   - **合計**: 5 × 9 = 45プロセス追加
   - **メモリ/FD枯渇のリスク**

2. **ロック順序問題**:
   - ワーカープロセス A が Manager 起動待機
   - ワーカープロセス B も Manager 起動待機
   - メインプロセスが両者の完了を待つ
   - ⟹ 循環待機

3. **multiprocessing.Manager の動作**:
   - Manager は**別プロセス**として動作
   - そのプロセスはメインプロセスの fork で生成される
   - ProcessPoolExecutor 内部では fork 安全性が保証されない

---

## コード上の問題箇所

### 1. generate_single_fits_tiles.py - Line 79

```python
def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    # ★ PROBLEM: multiprocessing.Manager() を RPC ワーカー内で作成
    with tempfile.TemporaryDirectory() as tmpdir, \
         multiprocessing.Manager() as manager:
        q = cast(
            queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata | None],
            manager.Queue(),
        )
        # ...
        with multiprocessing.Pool(8) as pool:  # ★ さらに Pool
            for ccd_metadata in pool.imap_unordered(
                _process_ccd,
                (ProcessCcdArgs(..., q, ...) for ref, path in ccd_paths()),
            ):
                q.put(ccd_metadata)
```

### 2. rpc/server.py - Line 189-198

```python
# ProcessPoolExecutor からの呼び出し
future = pool.submit(
    _execute_function_in_process,
    func,  # ← この func は _generate_single_fits_tiles_rpc
    tuple(processed_args),  # refs が Iterable で pickled
    processed_kwargs,
    queue_map,
    result_queue,
)
```

---

## 根本原因の分析

### A. ネストしたプロセス生成の問題

| レベル | 何をしている | プロセス数 |
|--------|------------|---------|
| 0 | pytest メインプロセス | 1 |
| 1 | ProcessPoolExecutor 作成 | +5 |
| 2 | ワーカー内で Manager 作成 | +1 per worker = +5 |
| 3 | ワーカー内で Pool 作成 | +8 per worker × 5 = +40 |
| **合計** | | **51** |

### B. fork と asyncio の互換性問題

- generator内で`multiprocessing.Manager()`を呼ぶ
- Manager は `spawn` コンテキストを使う (fork ではない)
- しかし asyncio ループ内での fork は危険

### C. イベントループとマルチプロセッシングの交錯

```python
async def create_rpc_endpoint(app: FastAPI, ws: WebSocket) -> None:
    # ...
    future = pool.submit(...)  # ← 同期プロセスプール
    # ProcessPoolExecutor は内部で独自のスレッドを使用
```

---

## 修正アプローチ

### 案1: Generator 出力への修正（推奨）

**問題**: `generate_single_fits_tiles_pipeline` が`multiprocessing.Manager`を作成

**解決**: Manager を外部で作成し、引数として渡す

```python
def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
    manager: multiprocessing.Manager | None = None,  # ← 追加
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    should_close_manager = manager is None
    manager = manager or multiprocessing.Manager()
    
    try:
        # ... 既存コード ...
    finally:
        if should_close_manager:
            manager.shutdown()
```

**利点**:
- ネストを1段階減らせる
- RPC 呼び出し側で Manager を一度作成→複数回利用

### 案2: ProcessPoolExecutor の廃止（中期改善）

**問題**: ProcessPoolExecutor でプロセス実行 → ネストが深い

**解決**: asyncio ネイティブな設計に変更

```python
# 代わりに
async def create_rpc_endpoint(app: FastAPI, ws: WebSocket) -> None:
    # ...
    # future = pool.submit(...) の代わり
    gen = _generate_single_fits_tiles_rpc(...)
    async for msg in gen:
        # 処理
```

**課題**: CPU バウンドな処理が AsyncIO で実行されると GIL に制限される

### 案3: Spawning コンテキストの明示（短期）

```python
import multiprocessing as mp

# Linux のデフォルトは 'fork'、Windows は 'spawn'
ctx = mp.get_context('spawn')  # 明示的に指定

with ctx.Manager() as manager:
    # ...
```

**効果**: 限定的（ネスティング問題は解決しない）

### 案4: マルチスレッド化（別の検討）

```python
from concurrent.futures import ThreadPoolExecutor

def generate_single_fits_tiles_pipeline(...):
    # multiprocessing.Pool の代わりに
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(_process_ccd_sync, args)
            for args in ccd_args_list
        ]
        for future in as_completed(futures):
            yield future.result()
```

**トレードオフ**:
- ✓ プロセス数が大幅に削減
- ✗ GIL の影響で CPU バウンド処理が遅くなる可能性

---

## 推奨される即座の対応

### ステップ 1: テストの並列度を制限

```bash
# pytest-xdist で並列ワーカー数を制限
pytest -n 2 src/quicklook/coordinator/create_quicklook/test_create_quicklook.py
```

### ステップ 2: Manager のネスティング回避

`_generate_single_fits_tiles_rpc` を修正:

```python
def _generate_single_fits_tiles_rpc(
    job: Job,
    ccd_refs_q: queue.Queue[CcdDataRef | None],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    # Manager をここで作成する代わり
    # Coordinator 側で作成済みのものを使う
    gen = generate_single_fits_tiles_pipeline(job, ccd_refs(), manager=existing_manager)
    try:
        for msg in gen:
            yield msg
    finally:
        gen.close()
```

### ステップ 3: デッドロック検出メカニズム

```python
# Timeout を設定してハング検出
def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
    timeout: float = 300,  # 5分
) -> Generator:
    with multiprocessing.Manager() as manager:
        # ...
        manager.shutdown(timeout=timeout)
```

---

## 検証方法

修正後の確認:

```bash
# 1. プロセス数の監視
while true; do pstree -p 2968184 | wc -l; sleep 1; done

# 2. テスト実行
make test

# 3. ハング検出
timeout 60 pytest -xvs src/quicklook/coordinator/create_quicklook/test_create_quicklook.py

# 4. メモリ使用量監視
watch -n 1 'pstree -p 2968184 | wc -l && ps aux | grep python | head -20'
```

---

## 関連ファイル

- **デッドロック分析**: `/home/michitaro/fov-quicklook2/backend/DEADLOCK_ANALYSIS.md`
- **プロセスツリー**: `/home/michitaro/fov-quicklook2/backend/backtrace_pstree.txt`
- **ログ**: `/home/michitaro/fov-quicklook2/backend/log` (SIGUSR1 でダンプ済み)
- **バックトレース取得スクリプト**: `/home/michitaro/fov-quicklook2/backend/collect_backtraces.sh`
- **個別プロセスバックトレース**: `/home/michitaro/fov-quicklook2/backend/backtrace_pid_*.txt` (66個)
