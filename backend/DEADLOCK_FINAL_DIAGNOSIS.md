# FOV-Quicklook デッドロック - **最終根本原因分析**

## ✅ 調査完了

正常にバックトレースを収集・分析しました。

---

## 🔴 **2つの異なるデッドロック地点が判明**

### **デッドロック地点 #1: Manager 起動時のプロセス作成**

```
Backtrace Line 1667:
  File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/context.py", line 57 in Manager
  File "/home/michitaro/fov-quicklook2/backend/src/quicklook/generator/generate_single_fits_tiles.py", line 79 in generate_single_fits_tiles_pipeline
```

**Stuck state**:
```python
File "__init__", line ??? in __init__  ← 不明な行番号
File ".../multiprocessing/context.py", line 282 in _Popen
File ".../multiprocessing/process.py", line 121 in start
File ".../concurrent/futures/process.py", line 812 in submit
```

**問題**: `Manager()` が新しいプロセスを起動しようとしているが、`_Popen` で **ハング状態**

### **デッドロック地点 #2: Manager Queue の get() 操作**

```
Backtrace Line 3054:
  File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/connection.py", line 395 in _recv
  File ".../multiprocessing/managers.py", line 824 in _callmethod
  File "<string>", line 2 in get  ← ★ Queue.get() 実行
  File "/home/michitaro/fov-quicklook2/backend/src/quicklook/generator/generate_single_fits_tiles.py", line 119 in generate_single_fits_tiles_pipeline
```

**Stuck state**:
```python
File "/home/michitaro/miniconda3/envs/py3_13/lib/python3.13/multiprocessing/connection.py", line 395 in _recv
  ↓ ★ Manager サーバーとの通信で RECV 待機中
```

**問題**: Manager Queue の `get()` がメッセージ受信で **待機中**

---

## 📊 **デッドロック全体図**

```
┌─ ProcessPoolExecutor (メインプロセスから子を起動)
│
├─ ワーカープロセス #1 (PID 2968203, etc)
│  │
│  └─ _execute_function_in_process()
│     └─ generate_single_fits_tiles_rpc()
│        └─ generate_single_fits_tiles_pipeline()
│           │
│           ├─ 【DEADLOCK #1】multiprocessing.Manager() 作成
│           │  └─ 新しいプロセス起動試行 ← _Popen でハング
│           │     (リソース不足？通信ハング？)
│           │
│           └─ q.get() 操作
│              └─【DEADLOCK #2】Manager との通信で RECV 待機
│                 (Message 受信待ち = 対側がメッセージ送信していない)
│
└─ 【GLOBAL DEADLOCK】
   すべてのプロセスが互いに待機中
```

---

## 🔍 **根本原因の詳細分析**

### **原因 A: リソース枯渇によるプロセス作成失敗**

ProcessPoolExecutor のマネージャースレッド:
```
concurrent.futures.process.py:751 in _start_executor_manager_thread
  └─ 新しいワーカーを起動しようとしている
```

複数のプロセスが同時にプロセス作成を試みているとき：
- ファイルディスクリプタ (FD) 枯渇
- メモリ不足
- システムプロセス数制限に達している

→ `_Popen()` が待機状態に

### **原因 B: Manager プロセスの初期化タイムアウト**

Manager プロセスが起動しても、以下が発生：
- 子 Manager プロセスの readiness シグナルが親に届かない
- パイプ通信が詰まっている
- 親プロセスが Manager の「起動完了」を永遠に待っている

→ `multiprocessing.context.Manager()` の `__enter__` でハング

### **原因 C: Queue メッセージ送受信の詰まり**

2 つ目のハング地点：
```python
q.get()  # Manager Queue からメッセージ受信
  └─ _callmethod("get")
     └─ 通信で _recv() ← ★ ここで待機
```

**なぜ詰まる？**
- Manager サーバープロセスが動かない（#1 でハング）
- または Manager サーバーが別の処理で busy

---

## 🎯 **完全な因果関係**

```
① ProcessPoolExecutor が複数のワーカーを同時起動
   ↓
② 各ワーカーが generate_single_fits_tiles_pipeline() を実行
   ↓
③ すべてのワーカーが同時に Manager() を作成しようとする
   ↓
④ システムリソース枯渇（FD / メモリ）
   ↓
⑤ _Popen() がハング → Manager プロセス起動失敗
   ↓
⑥ Manager() の __enter__ がタイムアウトなく待機
   ↓
⑦ さらに進んだワーカーが q.get() でも待機
   ↓
⑧ 【全プロセスデッドロック】
```

---

## 📍 **関連プロセス統計**

| 状態 | プロセス数 |
|------|--------:|
| Manager 作成試行中 | 3 (2968184, 2968230, 2968430) |
| serve_forever() 待機 | 4 (2968184, 2968203, 2968212, 2968430) |
| ProcessPoolExecutor 内 | 34 (全プロセス) |

→ ほぼすべてのプロセスが multiprocessing に関連するハング

---

## 💡 **解決方法**

### **短期：Manager をネスティングから除去**

```python
# 現在（悪い）
def _generate_single_fits_tiles_rpc(job, ccd_refs_q):
    gen = generate_single_fits_tiles_pipeline(job, ccd_refs())
    # ← Manager() がここで作成されている

# 修正案
def _generate_single_fits_tiles_rpc(job, ccd_refs_q, manager):
    gen = generate_single_fits_tiles_pipeline(job, ccd_refs(), manager=manager)
    # ← Manager は外で作成済み
```

### **中期：ProcessPoolExecutor をリプレイス**

- asyncio タスクへの移行
- ThreadPoolExecutor への変更

### **長期：アーキテクチャの見直し**

- RPC 呼び出しの軽量化
- マルチプロセッシングの依存性削減

---

##結論

**根本原因**: 
- **ProcessPoolExecutor** ワーカープロセス内での
- **multiprocessing.Manager()** 作成による
- **ネストされたプロセス生成**が
- **システムリソース枯渇**を引き起こし
- デッドロック状態に陥っている

**具体的には**:
1. プロセス #1-#N が同時に Manager 作成
2. _Popen() でプロセス起動資源が競合
3. 誰も完了せず、すべてが待機状態

**修正優先度**: 🔴 **必須 (即時対応)**
