# Coordinator - Generator 間の通信

Coordinatorは、Generatorに対してjobの実行を指示する。
そのために前もってCoordinatorは利用可能なGeneratorのリストを保持しておく必要がある。
以下の前提でその仕組みを考える。

* システム全体でCoordinatorは１つだけ存在する。
* システム全体でGeneratorは複数存在する。
* Coordinator, Generatorは突発的に停止することがある。(k8sで動作するため)

## 実装

* Generator, CoordinatorはどちらもFastAPIのアプリケーションとして実装する。
* Generator
  * 定期的（起動時にも）にCoordinatorに対して自分の存在を通知する。
  * この時にアクセスしたCoordinatorを覚えておく。
  * そのCoordinatorからのRPCは受け付ける。
  * 定期的にそのCoordinatorに対して疎通確認。
    * 疎通失敗した場合、これはCoordinatorが停止したとみなす。
    * 自プロセスを終了する。（再起動はK8sに任せる）
* Coordinator
  * Generatorからの通知を受け付ける。
  * そのGeneratorを利用可能なGeneratorとして登録する。
  * 登録されているGeneratorに対して定期的に疎通確認。
    * 疎通失敗した場合、そのGeneratorは利用不可とみなす。
    * そのGeneratorを利用可能なGeneratorのリストから削除する。

## モジュールインターフェース

### Generator

```python
from quicklook.comm import coordinator

app = FastAPI(lifespan=coordinator.lifespan)
app.include_router(coordinator.router)

@app.post("/job")
async def job(request: JobRequest) -> JobResponse:
    async scatter_job(coordinator.generators()):
      pass
```

### Coordinator

```python
from quicklook.comm import generator

app = FastAPI(lifespan=generator.lifespan)
app.include_router(generator.router)
```

### Types

```python
from dataclasses import dataclass

@dataclass
class GeneratorInfo:
    host: str
    job_slots: int  # 同時に処理できるjobの数
```


のような形で利用する。

* `{coordinator,generator}.router`で必要なエンドポイントを作成する。
* `coordinator.generators()`で`GeneratorInfo`のリストを取得できる。
