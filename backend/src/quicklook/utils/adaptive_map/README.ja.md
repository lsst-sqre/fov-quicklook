# Adaptive Map

このアプリではFITSファイルからのタイル生成を複数のpodで分散して処理する。
これらのpodはことなるk8sノードで動作することがあり性能にばらつきがある。
そのため最初にすべてのFITSファイルを均等に割り当てると、性能の低いpodがボトルネックになり全体の処理が遅くなる。
実際`usdf-dev`環境ではなんらかの理由で非常にレスポンスの悪いpodが存在し、全体の処理が非常に遅くなってしまうことがあった。

その問題の解消のために、各podへのFITSファイルの割り当てを動的に行うことを考える。

## 概念

ここでは問題を一般化して次のような状況を考える。

* 処理を行う主体を`Worker`とする。
* 各`Worker`はそれぞれ異なる性能を持ち、同じ処理をしてもかかる時間が同じとは限らない。
    * `Worker`は具体的には他のプロセスやノードを抽象化したもの。
* 処理の対象の列を`items: list[Item]`とする。
    * `items`には同じ値を複数回含めてもよい。各要素は独立したスケジュール対象として扱われる。
    * `Item`はハッシュ可能でなくてもかまわない（例: `dict` や `list`）。`adaptive_map`は各要素の位置情報で内部管理を行うため、値の同一性やハッシュ可能性に依存しない。

## 仕様

* `Worker`は次ののようなインターフェースを持つ。

    ```python
    class Worker:
        def capacity(self) -> int:
            '''
            現在のsubmitの受付可能な処理数を返す
            この値は通常submitされると1減少する
            '''
            ...

        async def submit(self, func: Callable[..., Awaitable], *args, **kwargs):
            '''
            workerに非同期関数funcの処理を依頼する
            '''
            ...    

        async def wait_until_available(self):
            '''
            workerが利用可能になるまでブロック
            '''
            ...

        async def teardown(self):
            '''
            ワーカーをクリーンアップする
            '''
            ...
    ```
    * これは`ThreadPoolExecutor`や`ProcessPoolExecutor`のインターフェースに似ている。
    * これはユーザーが提供してもよいし、`teardown`, `max_concurrency`, `submit`から`Worker`をつくるヘルパー関数から生成することもできる。

### ヘルパー関数を使ったWorkerの実装例

ヘルパー関数`create_worker`を使うと、`teardown`、`max_concurrency`、`submit`から簡単にWorkerを作成できる：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Awaitable, Any
from . import create_worker

# asyncioのrun_in_executorを使ったWorker
def create_executor_worker(max_workers: int = 1) -> Worker:
    executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def teardown():
        executor.shutdown(wait=True)
    
    async def submit(func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        # 非同期関数をスレッドプールで実行
        def sync_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()
        
        # run_in_executorを使用してスレッドプールで実行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, sync_wrapper)
        return result
    
    return create_worker(teardown, max_workers, submit)

# HTTPクライアントを使った分散Workerの例
def create_http_worker(endpoint: str, max_concurrency: int = 1) -> Worker:
    import aiohttp
    
    session = None
    
    async def teardown():
        nonlocal session
        if session:
            await session.close()
    
    async def submit(func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        nonlocal session
        if not session:
            session = aiohttp.ClientSession()
        
        # リモートサーバーに処理を依頼する例
        # 実際の実装では適切なAPIエンドポイントを使用
        async with session.post(
            f"{endpoint}/process",
            json={"args": args, "kwargs": kwargs}
        ) as response:
            if response.status == 200:
                result_data = await response.json()
                return result_data["result"]
            else:
                raise RuntimeError(f"Remote worker failed: {response.status}")
    
    return create_worker(teardown, max_concurrency, submit)
```

ヘルパー関数で作成されるWorkerは以下の特徴を持つ：
- `submit`されると自動的に`capacity`を減らし、引数の`submit`を実行し、実行が終われば`capacity`を増やす
- `wait_until_available`の実装：`submit`された処理が終わったタイミングで`capacity`が0以上になっていたらブロックを解除

* 使い方は次のようになる。

    ```python
    workers: list[Worker] # 処理を行う主体のリスト
    items: list[Item] # 処理対象
    func: Callable[[Item], Awaitable[Result]]

    async for map_result in adaptive_map(workers, func, items):
        print(map_result.value) # map_result.valueはMapResult型
    ```

    * `map_result`は次のような型である。

        ```python
        @dataclass
        class MapResult:
            worker: Worker
            item: Item
            value: Any
            execution_time: float
        ```

* `adaptive_map`は次のように動作する。
    * `workers`のどれかが`capacity() > 0`である限り、`items`を順次`submit`する
        * `workers`のどれかが利用可能になるまで待機し、その後再び`items`を`submit`する
    * `item`の処理が終わったら即時それに関する`MapResult`を`yield`する
        * 同じ値を持つ`item`が複数あっても、それぞれが独立に`yield`される。
        * `MapResult.item`は常に元の`items`リスト内のオブジェクトそのものを指す。
    * リスケジュール
        * すべての`items`が`submit`されたあも実行中のitemがあれば、それはリスケジュールの対象となる可能性がある。
        * そのようなitemはストールしたworkerにスケジュールされた可能性がある。
        * このタイミングまでに完了したitemsの処理にかかった時間の中央値の2倍以上の時間がかかっているitemはcapacityの最大の利用可能なworkerに`submit`する。
            * この時、実行中のitemをcancelするかどうかはオプションで切り替えられる。
        * リスケジュールされたitemは2回以上実行される可能性がある。
            * 1回目に完了した結果がyieldされ、2回目以降に完了したものは`adaptive_map`のオプション`on_late_result: Callable[[MapResult], None]`に渡される。
    * workerの停止
        * workerは外部の要因で停止することがある。
        * `func`でworkerの停止を検出し、その場合`WorkerDown`を送出する
        * itemの処理中に`WorkerDown`例外が発生した場合
            * そのworkerは`teardown`される。
            * そのworkerはリスケジュールの対象から外れる。
            * そのworkerにスケジュールされていたitemはリスケジュールされる。
    * 例外
        * `func`内で例外が発生したらそれはそのまま`adaptive_map`に伝播される。
    * pollingはしない
        * 次のitemのsubmitやリスケジュールは、どれかのworkerで`wait_until_available`が完了したタイミングで行えばよい。pollingは行わない。

## 動作パターンの例

以下は`asyncio.sleep(0.1)`を処理として使った場合の予想される動作パターンです。
各パターンは`(items数, capacity, worker数, 予想処理時間)`の形式で表記しています。

### シンプルなケース

1. **並列処理なし**: `(2, 1, 1, 0.2)`
   - 2つのアイテムを1つのワーカー（capacity=1）で順次処理
   - 各アイテムが0.1秒なので合計0.2秒

2. **キャパシティによる並列化**: `(2, 2, 1, 0.1)`
   - 2つのアイテムを1つのワーカー（capacity=2）で同時処理
   - 並列実行により0.1秒で完了

3. **ワーカー数による並列化**: `(2, 1, 2, 0.1)`
   - 2つのアイテムを2つのワーカー（各capacity=1）で並列処理
   - 各ワーカーが1つずつ処理して0.1秒で完了

4. **完全並列**: `(3, 1, 3, 0.1)`
   - 3つのアイテムを3つのワーカー（各capacity=1）で並列処理
   - すべて同時実行で0.1秒で完了

### より複雑なケース

5. **ワーカー数がボトルネック**: `(4, 1, 2, 0.2)`
   - 4つのアイテムを2つのワーカーで処理
   - 2つずつ2回に分けて処理するため0.2秒

6. **容量がボトルネック**: `(4, 2, 1, 0.2)`
   - 4つのアイテムを1つのワーカー（capacity=2）で処理
   - 2つずつ2回に分けて処理するため0.2秒

7. **混合並列**: `(6, 2, 2, 0.2)`
   - 6つのアイテムを2つのワーカー（各capacity=2）で処理
   - 各ワーカーが2つずつを2回処理するため0.2秒

### リスケジューリングケース

8. **性能差のあるワーカー**: `(4, 1, 2, 0.15)`
   - ワーカー1: 通常速度（0.1秒/アイテム）
   - ワーカー2: 低速（0.2秒/アイテム）
   - 中央値の2倍（0.2秒）を超えるアイテムがリスケジュールされる可能性
   - 最終的に高速ワーカーに集約され約0.15秒で完了

これらのパターンは理想的な状況を仮定しており、実際にはワーカーの初期化時間、タスクのスケジューリングオーバーヘッド、リスケジューリングの判定時間などが加算されます。