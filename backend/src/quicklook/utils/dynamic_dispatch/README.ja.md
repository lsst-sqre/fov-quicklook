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
* `Worker`は`Worker`ごとに決まった数までの`Item`の処理を並列で行うことができる（capacity）。
  * 例えば`capacity=2`の`Worker`は、2つの`Item`を同時に並列処理できる。
* `Worker.run`は冪等性を持つ。つまり同じ`Item`を複数の`Worker`で処理しても問題ない。
* `Worker.run`は`Worker`の状態によって処理が失敗する場合がある。
    * 例えば`Worker`が落ちている場合など。`Worker.run`が送出する`WorkerDownError`で検出できる。
* `Worker`のインスタンスによって性能が異なるため、先に処理を開始したのに後から処理が終わることがある。

### 実装

* `items: Iterable[Item]`から各Workerのcapacityに応じてitemを取り出し、利用可能な`Worker`にdispatchする(`Worker.run`を呼び出す)ことを繰り返す。
  * 全Workerが容量上限に達した場合は、`Worker`に空きができるのを待つ。
* `items`が空になって、処理中のitemがあれば、それを空いている`Worker`に割り当てる。
  * これは長時間実行中のタスクを高速なWorkerに再配置する機能として実装されている。
  * 完了したタスクの実行時間の中央値の2倍を超えて実行中のタスクのみが再配置対象となる。
  * 再配置対象のタスクは最も古いもの（開始時刻順）から順に処理される。
  * 利用可能な高速Workerにキャンセル・再実行される。
* 全ての`items`の処理が終わったら終了する。
* `WorkerDownError`が発生したら、失敗した`Item`を`items`に戻し、その`Worker`は`kill`して以降使わない。
  * この処理に関しては`dynamic_dispatch`のオプションで切り替えられるようにする。
* `dynamic_dispatch`は結果を`AsyncIterator[Result]`として返す。`Result`からはどの`Worker`で処理したかがわかるようにする。
* 処理が完了したものから順次yieldされる。
* 遅い`Worker`に割り当たった`Item`は、（他の高速な`Worker`が空き時間に処理してしまって）一度全ての処理が終わった後に完了するかもしれない。
  `dynamic_dispatch`にはその場合のcallbackを登録できるようにする。

## 並列処理のサポート

各`Worker`は複数の`Item`を並列処理できる。例えば：

* `capacity=2`の`Worker`が2つの`time.sleep(0.1)`相当の処理を行う場合、約0.1秒で完了する
* `capacity=1`の`Worker`が2つの`time.sleep(0.1)`相当の処理を行う場合、約0.2秒で完了する

`dynamic_dispatch`は各`Worker`の固定`capacity`値を使用して容量管理を行い、
容量の範囲内で複数のタスクを並列で割り当てる。

## 新しいインターフェース

Workerは以下のdataclassとして定義される：

```python
from typing import Callable, Coroutine, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class Worker:
    run: Callable[[Item], Coroutine[Any, Any, R]]
    kill: Callable[[], Coroutine[Any, Any, None]]
    capacity: int  # 固定の容量値

@dataclass
class Result:
    item: Item
    worker: Worker
    value: R  # 処理結果 Worker.runの結果
    execution_time: float

async def dynamic_dispatch(
    workers: list[Worker],
    items: Iterable[Item],
    *,
    retry_on_worker_down: bool = True,
    on_late_result: Callable[[Result], Awaitable[None]] | None = None,
    max_redistribution_count: int = 2,
) -> AsyncIterator[Result]:
    ...
```

### 主な変更点

1. **Worker定義**: Protocolからdataclassに変更
2. **capacity管理**: Workerの固定プロパティとして定義。実行中のタスク数はdynamic_dispatch内部で管理
3. **タスク再配置**: 完了したタスクの実行時間の中央値に基づく適応的な再配置機能
4. **型安全性**: `Coroutine`型を明示的に使用してasyncio互換性を保証
5. **最大再配置回数**: `max_redistribution_count`パラメータで無限たらい回しを防止

### タスク再配置機能

新しい機能として、長時間実行中のタスクを高速なWorkerに自動再配置する機能が追加された：

* すべての`items`が一度dispatchされた後、通常はworkerの空きがなくなる
* workerの空きができた際に`redistribute_running_tasks`が呼び出される
* この時点で、通常いくつかの処理が既に完了している
* **完了したタスクの実行時間の中央値の2倍**を超えているタスクのみを再配置の対象とする
  * 完了したタスクが1つもない場合は、中央値は0として扱い、すべてのタスクが対象となる
* 再配置対象となる実行中のタスクは**最も古いもの（開始時刻順）から順に**処理される
* 利用可能な容量を持つWorkerがあれば、長時間実行中のタスクをキャンセルして再実行
* 全体的な処理時間の短縮と、遅いWorkerによるボトルネック解消を実現
* 無限たらい回しを防ぐため、各アイテムの最大再配置回数制限が設けられている

この改善により、より適応的で効率的な負荷分散が実現される。
