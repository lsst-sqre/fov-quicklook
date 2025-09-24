# 🌀 AsyncProcessGenerator — 重い処理を別プロセスで非同期ストリーミング

`run_async_process_generator` は、**CPUバウンドな重い処理やブロッキングI/Oを含んだジェネレーター関数**を、  
**別プロセスで実行しつつ、`async generator` として逐次結果を取得できる**ようにするユーティリティ関数です。

## ✨ 特徴

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

## 📝 使い方

### 基本的な利用

```python
import asyncio

def heavy_generator(count: int):
    """重い処理を含むジェネレーター関数の例"""
    import time
    for i in range(count):
        # 重い処理をシミュレート
        time.sleep(1)
        yield f"処理完了: {i + 1}/{count}"

async def main():
    async for result in run_async_process_generator(heavy_generator, 5):
        print(f"受信: {result}")

# 実行
asyncio.run(main())
```

### FastAPI x StreamingResponse

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

def heavy_data_processing(data_size: int):
    """重いデータ処理のジェネレーター"""
    import time
    for i in range(data_size):
        # CPU集約的な処理
        time.sleep(0.5)  # 重い処理をシミュレート
        yield f"データ {i+1} 処理完了"

@app.get("/stream/{count}")
async def stream_heavy_process(count: int):
    return StreamingResponse(
        create_streaming_response_from_process(heavy_data_processing, count),
        media_type="text/plain"
    )

@app.get("/direct-stream/{count}")
async def direct_stream(count: int):
    """直接async generatorを使用する場合"""
    async def response_generator():
        async for result in run_async_process_generator(heavy_data_processing, count):
            yield f"{result}\n"

    return StreamingResponse(response_generator(), media_type="text/plain")
```

## 🔧 パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `generator_func` | `Callable` | - | 実行する同期ジェネレーター関数 |
| `*args` | `Any` | - | ジェネレーター関数に渡す位置引数 |
| `timeout` | `float` | `1.0` | Queue取得のタイムアウト秒数 |
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

## 🚀 まとめ

`run_async_process_generator` を使えば、**「非同期なFastAPIアプリ」 + 「同期的で重い処理」** をうまく分離し、スケールしやすい構成が作れます。

メインプロセスのイベントループをブロックすることなく、重い処理の結果をリアルタイムでストリーミングできる強力なユーティリティです。
