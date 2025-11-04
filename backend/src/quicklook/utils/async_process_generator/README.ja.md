# 🌀 AsyncProcessGenerator — 重い処理を別プロセスで非同期ストリーミング

**プロセスプール**を使用して、**CPUバウンドな重い処理やブロッキングI/Oを含んだジェネレーター関数**を  
**別プロセスで実行しつつ、`async generator` として逐次結果を取得できる**ようにするユーティリティです。

## ✨ 特徴

- **プロセスプールによる効率的な実行**  
  → 呼び出しのたびにプロセスを作らず、既存のワーカープロセスを再利用  
- **別プロセスで実行**  
  → イベントループや他リクエストをブロックしない  
- **リアルタイムストリーミング**  
  → `yield` した値を逐次 async generator で受け取れる  
- **エラー伝播**  
  → プロセス内で発生した例外も呼び出し側に re-raise  
- **クリーンアップ**  
  → プロセス終了処理を自動で管理  
- **FastAPI / StreamingResponse 対応**  
  → Web API での逐次レスポンス生成にそのまま利用可能  
- **初期化関数サポート**  
  → ワーカープロセス起動時に初期化処理を実行可能  

## 📝 使い方

### 基本的な利用

```python
import asyncio
from quicklook.utils.async_process_generator import create_async_process_pool

def heavy_generator(count: int):
    """重い処理を含むジェネレーター関数の例"""
    import time
    for i in range(count):
        # 重い処理をシミュレート
        time.sleep(1)
        yield f"処理完了: {i + 1}/{count}"

async def main():
    # プロセスプールを作成
    async with create_async_process_pool(max_workers=4) as pool:
        async for result in pool.run_async_process_generator(heavy_generator, 5):
            print(f"受信: {result}")

# 実行
asyncio.run(main())
```

### FastAPI lifespanでの利用

FastAPIアプリケーションのlifespanでプロセスプールを管理し、リクエストハンドラで使用します。

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from quicklook.utils.async_process_generator import create_async_process_pool

# グローバルなプロセスプール
_process_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _process_pool
    # プロセスプールを初期化
    async with create_async_process_pool(max_workers=4) as pool:
        _process_pool = pool
        try:
            yield
        finally:
            _process_pool = None

app = FastAPI(lifespan=lifespan)

def heavy_data_processing(data_size: int):
    """重いデータ処理のジェネレーター"""
    import time
    for i in range(data_size):
        # CPU集約的な処理
        time.sleep(0.5)  # 重い処理をシミュレート
        yield f"データ {i+1} 処理完了\n"

@app.get("/stream/{count}")
async def stream_heavy_process(count: int):
    if _process_pool is None:
        raise RuntimeError("Process pool not initialized")
    
    return StreamingResponse(
        _process_pool.run_async_process_generator(heavy_data_processing, count),
        media_type="text/plain"
    )
```

### 初期化関数の使用

ワーカープロセスの起動時に初期化処理を実行できます。

```python
from quicklook.utils.async_process_generator import create_async_process_pool

# グローバル変数（各ワーカープロセスで独立）
_db_connection = None

def initialize_worker():
    """ワーカープロセスの初期化"""
    global _db_connection
    _db_connection = connect_to_database()
    print(f"Worker initialized with DB connection")

def query_generator(query: str):
    """DBクエリを実行するジェネレーター"""
    global _db_connection
    cursor = _db_connection.execute(query)
    for row in cursor:
        yield row

async def main():
    # 初期化関数を指定してプロセスプールを作成
    async with create_async_process_pool(
        max_workers=4,
        initializers=[initialize_worker]
    ) as pool:
        async for row in pool.run_async_process_generator(query_generator, "SELECT * FROM users"):
            print(row)
```

## 🔧 パラメータ

### `create_async_process_pool`

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `max_workers` | `int \| None` | `None` | プロセスプールのワーカー数（Noneの場合はCPU数） |
| `initializers` | `list[Callable[[], None]] \| None` | `None` | 各ワーカープロセスで実行する初期化関数のリスト |

### `pool.run_async_process_generator`

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `generator_func` | `Callable` | - | 実行する同期ジェネレーター関数 |
| `*args` | `Any` | - | ジェネレーター関数に渡す位置引数 |
| `**kwargs` | `Any` | - | ジェネレーター関数に渡すキーワード引数 |

## 📦 ユースケース

- **大規模ファイル処理**  
  逐次読み書き・加工処理をメインプロセスをブロックせずに実行

- **CPUバウンド計算**  
  機械学習モデルの逐次生成結果、画像処理、数値計算など

- **ストリーミング応答**  
  Server-Sent Events (SSE) や FastAPI `StreamingResponse` での逐次レスポンス

- **長時間処理の進捗表示**  
  バッチ処理の進捗をリアルタイムでフロントエンドに送信

## ⚠️ 注意事項

- **プロセス間通信のオーバーヘッド**  
  小さなデータを頻繁にyieldする場合は、スレッドプール (`anyio.to_thread`) の方が効率的な場合があります

- **pickle可能なオブジェクト**  
  yieldする値はpickle可能である必要があります（基本的なPython型は問題なし）

- **メモリ使用量**  
  Queueにバッファリングされるため、大量のデータを一度にyieldする場合は注意

## � 移行ガイド（旧APIから）

以前の`run_async_process_generator`関数を直接使用していた場合は、以下のように書き換えてください。

**旧コード:**
```python
async for item in run_async_process_generator(my_generator, arg1, arg2):
    process(item)
```

**新コード:**
```python
async with create_async_process_pool() as pool:
    async for item in pool.run_async_process_generator(my_generator, arg1, arg2):
        process(item)
```

FastAPIアプリケーションの場合は、lifespanでプロセスプールを管理することを推奨します（上記の例を参照）。

## 🚀 まとめ

`create_async_process_pool` を使えば、**「非同期なFastAPIアプリ」 + 「同期的で重い処理」** をうまく分離し、スケールしやすい構成が作れます。

プロセスプールにより、呼び出しのたびにプロセスを作成するオーバーヘッドを削減し、メインプロセスのイベントループをブロックすることなく、重い処理の結果をリアルタイムでストリーミングできる強力なユーティリティです。
