# RPC２

## 概要

このアプリケーションではノード間が協調し処理を行う場面がある。
通信はhttpはwebsocketを通じて行われるが、数ある協調処理のすべての場面で通信の処理を書くのは煩雑である。

このため、通信の処理を抽象化することで、協調処理のコードを簡潔にしたい。
このメリットは呼び出される側の関数から通信の処理を排除することでテストをしやすくすることにもある。

一番簡単なケースは次のようなものである。

```python
def f(arg1, arg2):
    ...

result = await Rpc(f, arg1, arg2).run()
```

これは他ノードで同期関数を呼び出し非同期で受け取るケース。
他ノードで実行する関数は同期関数に限る。
(実行時に非同期関数だった場合はエラーを出す)

ターゲット関数がgeneratorの場合には

```python
def f():
    for i in range(5):
        yield i

async for j in Rpc(f).run():
    print(j)
```

のようなこともできる。

最後に対応したいケースとして呼び出し側の入力がqueueのケースである。

```python
import asyncio
import queue

client_queue = asyncio.Queue()

def f(q: queue.Queue):
    while True:
        item = await q.get()
        if item is None:
            break
        yield item

async def produce():
    for i in range(5):
        await client_queue.put(i)
    await client_queue.put(None)

task = asyncio.create_task(produce())

async for i in Rpc(rpc_endpoint_url, f, RpcQueue(client_queue)).run():
    print(i)
```

以上のコードはクライアントからの利用時のものである。

サーバーサイドでは↓のようにRPCのエンドポイントを定義する。


```python
from fastapi import FastAPI, WebSocket

app = FastAPI(lifespan=rpc_lifespan)

@app.post("/rpc")
async def rpc_endpoint(ws: WebSocket):
    return await create_rpc_endpoint(ws)
```

このような`Rpc`, `RpcQueue`, `rpc_endpoint`, `create_rpc_endpoint`などの関連する必要なクラスや関数を実装する。

## 実装要件

* コードベース内にはすでにrpcという名前のコードが存在するが、それとは完全に独立した新しいモジュールとして実装する。
* このファイルのディレクトリ内に必要なファイルを配置する。
* サーバーサイド(RPCで呼び出される側)はFastAPIでRPCリクエストを受け取る。
    * サーバー・クライアント間の通信はWebSocket(`websockets`モジュール)を使用する。
    * pickle化したオブジェクトをWebSocketで送受信する。
* サーバーサイドで実行する関数は同期関数のみ
* クライアントサイドでは結果は非同期で受け取る。
* サーバーサイドではRPCの呼び出しごとにプロセスプールを利用して別プロセスで実行する。
    * そのためのFastAPIの`lifespan`の`contextmanager`を実装する。
* 型ヒントを積極的に活用する。
    * `ParamSpec`や`@overload`を活用する。
* 通信はいくつかの種類のメッセージを使うことになるが、それらの種類の分岐にはPythonのmatch文を積極的に使う。
* 必要な機能を分解して単体で動作するように設計しそれぞれテストを行う。
* 細かい単位で`git commit`を行うこと。
* サーバーサイドでエラーが起きた場合はクライアントでは`RpcRemoteError`例外を発生させる。
* `RpcQueue`は`asyncio.Queue`を受け取り、型として`queue.Queue`を返す。
    * 実際には`RpcQueue`のインスタンスはリモートに送られるときに独自の取り扱いがされ、ノード間を繋ぐキューとして動作する。
* 開発時の注意
    * `./.venv`にPython環境があるのでそれを使う。
    * シェルの機能を使う時は`fish`が動くことを前提にする。
    * テスト
        * この手のモジュールはデッドロックに陥ることがある。テストにタイムアウトを指定すること。
            * `timeout 10 ./.venv/bin/pytest ...` のような使い方が良いだろう。
        * テストのカバレッジは100%を目指す。例外を送出するだけのブランチは通らなくても良い。(そのようなブランチは`#pragma: no branch`を使って良い。)