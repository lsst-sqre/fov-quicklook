# Coordinator - Generator 間の通信

Coordinatorは、Generatorに対してRPCを発行してジョブの実行を依頼する。
(Generatorはこのアプリケーション特有の呼び方で、一般的にはWorkerの役割を果たす。)
CoordinatorはRPCの前に利用可能なGeneratorのリストを保持しておく必要がある。
以下の前提でCoordinatorからGeneratorへの通信を確保する仕組みを考える。

* システム全体でCoordinatorは１つだけ存在する。
* システム全体でGeneratorは複数存在し、Coordinatorはそれらを(`dynamic_dispatch`などで)利用する。
* Coordinator, Generatorは突発的に停止することがある。(k8sで動作するため)

## 実装

* Generator, CoordinatorはどちらもFastAPIのアプリケーションとして実装する。
* Generator
  * 定期的（起動時にも）にCoordinatorに対して自分の存在を通知する。
    * 次を通知する
      * 自プロセスのRPC受付のポート番号
      * 同時に処理できるジョブの数
    * 疎通失敗した場合
      * Coordinatorが停止したかネットワーク障害が起きている。
      * 自プロセスを終了する。（再起動はK8sに任せる）
* Coordinator
  * Generatorからの通知を受け付ける。
  * そのGeneratorを利用可能なGeneratorとして登録する。
  * 登録されているGeneratorに対して定期的に疎通確認。
    * 疎通失敗した場合、そのGeneratorは利用不可とみなす。
    * そのGeneratorを利用可能なGeneratorのリストから削除する。

* 疎通確認はretryしない
  * 不安定状態になったら積極的に再起動する

## モジュールインターフェース

### Generator

```python
from quicklook.comm import coordinator

app = FastAPI(lifespan=coordinator.lifespan)
app.include_router(coordinator.router)

# ユーザーからのリクエストですべてのgeneratorにジョブをサブミット
@app.get('/available_generators')
async def available_generators():
    return coordinator.get_available_generators()
```

### Coordinator

```python
from quicklook.comm import generator

app = FastAPI(lifespan=generator.lifespan)
app.include_router(generator.router)
```

のような形で利用する。

* `coordinator.router`で必要なエンドポイントを作成する
  * `/healthz`
    * Generatorからの疎通確認
  * `/register`
    * Generatorからの登録
* `generator.router`で必要なエンドポイントを作成する
  * `/healthz`
    * Coordinatorからの疎通確認
  * `/rpc`
    * CoordinatorからのRPC呼び出しを受け付ける

