# デッドロック分析レポート

## 概要

PID 2968184のpytest プロセスツリーが`multiprocessing.Manager`に関連するデッドロックでハングアップしています。

## デッドロックの根本原因

### 問題のシナリオ

1. **RPC呼び出しチェーン**:
   - `websocket_rpc_endpoint` (generator/api/app.py:46)
   - `create_rpc_endpoint` (rpc/server.py:103)
   - `_setup_rpc_call` (rpc/server.py:189)
   - `pool.submit(_execute_function_in_process, ...)` (rpc/server.py:189)

2. **ワーカースレッド内での処理**:
   - `_execute_function_in_process` (rpc/server.py:324)
   - `_generate_single_fits_tiles_rpc` (coordinator/create_quicklook/generate_single_fits_tiles_coordinator.py:153)
   - `generate_single_fits_tiles_pipeline` (generator/generate_single_fits_tiles.py:79)

3. **デッドロック地点**:
   ```python
   # generate_single_fits_tiles.py line 79
   with multiprocessing.Manager() as manager:
       q = manager.Queue()  # Manager プロセスに接続しようとする
       # ...
       with multiprocessing.Pool(8) as pool:
           # Pool を使ってタイルを処理
           # ...
           pool.map(process_tile, ...)  # line 119 でキューから読み出し
   ```

### 具体的なデッドロック原因

バックトレースから判明:

1. **Managerプロセス起動の失敗**:
   ```
   File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/context.py", 
       line 57 in Manager
   ```
   - `Manager()` が新しいプロセスを起動しようとしている
   - ネストされたプロセス生成の複雑性がある

2. **ProcessPoolExecutor 内での Managerの起動**:
   ```
   concurrent/futures/process.py:812 in submit
   └─ ProcessPoolExecutor が子プロセスを起動
      └─ その子プロセス内で multiprocessing.Manager() を起動
         └─ さらに別のプロセスを起動しようとする
            └─ リソース枯渇またはロック競合
   ```

3. **ネストの深さ**:
   - メインプロセス (pytest runner)
     - ProcessPoolExecutor (5つのワーカー)
       - 各ワーカー内で
         - multiprocessing.Manager() (別プロセス)
           - multiprocessing.Pool(8) (8つのワーカー)
   
   **合計**: 1 + 5 + 5 + (5×8) = **51 プロセスが必要**

4. **リソース枯渇**:
   ```
   __init__", line ??? in __init__  # Popen が失敗または待機中
   multiprocessing/popen_fork.py", line 20 in __init__
   multiprocessing/context.py", line 282 in _Popen
   multiprocessing/process.py", line 121 in start
   ```
   - プロセス起動時にリソース取得のロック争いが発生
   - Managerプロセス起動時にfdやメモリが不足している

## バックトレース分析

### 2つのパターン

**パターン1**: Manager起動でハング（複数のバックトレース）
```
multiprocessing.context.Manager() -> _Popen() -> 待機中
```

**パターン2**: Manager Queue操作でハング
```
manager.Queue().get() が recv_bytes でハング
multiprocessing/connection.py:395 in _recv
multiprocessing/managers.py:824 in _callmethod
```

### 並行実行の問題

- PID 2968203, 2968212, 2968230 など複数のプロセスが同時にManager起動を試みている
- ProcessPoolExecutor のスレッドセーフティと multiprocessing のプロセス安全性のミスマッチ

## 現在のコード問題点

### 1. generate_single_fits_tiles.py (Line 76-95)

```python
def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    with tempfile.TemporaryDirectory() as tmpdir, \
         multiprocessing.Manager() as manager:  # ← ネストしたManager起動
        q = cast(
            queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata | None],
            manager.Queue(),
        )
        # ...
        with multiprocessing.Pool(8) as pool:  # ← Pool も作成
            # ...
            pool.map(...)  # ← 別プロセスからキュー通信
```

**問題**:
- `ProcessPoolExecutor` の子プロセス内で `Manager()` と `Pool()` を作成
- これらの作成はマルチレベルのプロセス生成を引き起こす
- 親プロセスがこれらのリソース初期化を待つ間にロック競合が発生

### 2. rpc/server.py (Line 189)

```python
future = pool.submit(
    _execute_function_in_process,
    func,
    tuple(processed_args),
    processed_kwargs,
    queue_map,
    result_queue,
)
```

**問題**:
- `ProcessPoolExecutor` の `pool.submit()` で、長時間実行される関数を実行
- その関数がさらに `Manager()` と `Pool()` を起動

## 解決方法

### 推奨策

1. **ネストしたプロセス生成を避ける**
   - `generate_single_fits_tiles_pipeline` を `ProcessPoolExecutor` の外で実行
   - または、スレッドベースの並列処理に変更

2. **Manager の使用をローカル化**
   - Manager は RPC呼び出しの前（Coordinator側）で作成
   - ワーカープロセスには既に作成されたキューのみを渡す

3. **multiprocessing.Pool から concurrent.futures.ThreadPoolExecutor へ変更**
   ```python
   # 代わりに
   with ThreadPoolExecutor(max_workers=8) as executor:
       # スレッド処理（GIL制約あるが、I/O待機時は効果的）
   ```

4. **テストの並列度を調整**
   - pytest の `-n` オプションで並列ワーカー数を制限
   - または、slow テストを分離

## その他の観察

- バックトレースが大量に出ている理由: 複数プロセスが同時にMana ger初期化でハング
- タイムアウト設定がないため、無限待機状態に陥っている
- リソース監視がないため、デッドロック検出が困難

## ファイル情報

- **プロセスツリー保存**: `/home/michitaro/fov-quicklook2/backend/backtrace_pstree.txt`
- **ログファイル**: `/home/michitaro/fov-quicklook2/backend/log` (849631 bytes)
- **バックトレース総行数**: 6525 行
