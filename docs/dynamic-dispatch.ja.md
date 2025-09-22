# 動的スケジューリング

複数の性能の違うgeneratorでタイル生成を行うため、動的にスケジューリングを行う必要がある。

1つのquicklookに対して189個ほどあるFITSファイルを複数のgeneratorで分担してタイル生成を行うが、
このときgeneratorの性能に差があると、単純にFITSファイルを均等に割り当てると、性能の低いgeneratorがボトルネックになってしまう。
そのため、FITSファイルの割り当ては動的に行う。
またいくつかのgeneratorは処理中になんらかの原因で落ちる（タイムアウトで検出する）ことを前提にする。
このノートではその方法を検討する。

## 概念

generatorなどこのアプリケーション特有の概念を使わずに抽象化してこの問題を考える。

* 処理を実際に行う主体を`Worker`と呼ぶ。`Worker`は複数あり、並列して動く。
* 処理の対象を`Item`と呼ぶ。`Item`は複数ある。
* `await worker.run(item)`で`Worker`が`Item`の処理を行う。
* `Worker`は`Worker`ごとに同時に決まった数までの`Item`の処理を行うことができる。
* `Worker.run`は冪等性を持つ。つまり同じ`Item`を複数の`Worker`で処理しても問題ない。
* `Worker.run`は`Worker`の状態によって処理が失敗する場合がある。
    * 例えば`Worker`が落ちている場合など。`Worker.run`が送出する`WorkerDownError`で検出できる。
* `Worker`のインスタンスによって性能が異なるため、先に処理を開始したのに後から処理が終わることがある。

### 実装

* `items: Iterable[Item]`から`pop(0)`でitemを取り出して最も空いている`Worker`にdispatchする(`Worker.run`を呼び出す)ことを繰り返す。
  * `Worker`に空きができるのを待つ。
* `items`が空になって、処理中のitemがあれば、それを空いている`Worker`に割り当てる。
* 全ての`items`の処理が終わったら終了する。
* `WorkerDownError`が発生したら、失敗した`Item`を`items`に戻し、その`Worker`は`kill`して以降使わない。
  * この処理に関しては`dynamic_dispatch`のオプションで切り替えら得るようにする。
* `dynamic_dispatch`は結果を`AsyncIterator[Result]`として返す。`Result`からはどの`Worker`で処理したかがわかるようにする。
* 処理が完了したものから順次yieldされる。
* 遅い`Worker`に割り当たった`Item`は、（他の高速な`Worker`が空き時間に処理してしまって）一度全ての処理が終わった後に完了するかもしれない。
  `dynamic_dispatch`にはその場合のcallbackを登録できるようにする。

インターフェースは次のようになる。

```python
from typing import Iterable, Protocol


@dataclass
class Result:
    item: Item
    worker: 'Worker'
    value: R  # 処理結果 Worker.runの結果

class Worker(Protocol):
    def capacity(self) -> int:
        # あと何個のItemを同時に処理できるか
        ...

    async def run(self, item: Item) -> R:
        # Itemの処理を行う
        ...

    async def kill(self):
        ...

async def dynamic_dispatch(
    workers: list[Worker],
    items: Iterable[Item],
    *,
    retry_on_worker_down: bool = True,
    on_late_result: Callable[[Result], Awaitable[None]] | None = None,
) -> AsyncIterator[Result]:
    ...
```
