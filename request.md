## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [ ] CPU使用率の実装の見直し

  `frontend/app/src/pages/admin/Status/index.tsx`でCPU使用率を表示していますが、値がマイナスになったりどうもおかしいです。
  この値の元になっているバックエンドのコードは`backend/src/quicklook/generator/api/app.py`の`route_get_status`の周辺です。
  バックエンド、フロントエンド両方のコードを見直し、問題を特定・修正してください。
  欲しい値は現在のCPU使用率です。例えば2CPUをフルに使っていれば200%と表示して欲しいです。

* [ ] バックエンドでgeneratorの終了処理

  generatorとcoordinatorは`backend/src/quicklook/comm`周辺のコードで連携している。
  coordinatorから特定のgeneratorを終了させるためのの仕組みを整備して下さい。
  `backend/src/quicklook/comm/coordinator.py`に`kill_generator(generator: GeneratorInfo)`のような関数を実装することになると思います。
  これを実行すると、指定したgeneratorプロセスが終了し、`get_available_generators`の結果にも現れなくなります。
  実現にはgeneratorに終了エンドポイントを作る必要があります。
  `backend/src/quicklook/comm/generator.py`の既存の`_shutdown`関数が使えるかもしれませんが、今回は待ち時間なしにすぐに終了してください。
  generatorは終了処理が始まったら、heatbeatは停止する必要があります。

* [ ] 処理速度の遅いgeneratorを終了させる

  `backend/src/quicklook/coordinator/create_quicklook/generate_single_fits_tiles_coordinator.py`の`generate_single_fits_tiles_coordinator`では複数のgeneratorに処理をdispatchしています。
  各タスクで処理にかかった時間を計測し、generatorごとの処理時間の中央値が全体の中央値の2倍以上かかったgeneratorがあれば、`kill_generator`を呼び出して終了させてください。

* [ ] バックエンドの`JobPriority`の`user_count`の増減を実装するAPIの追加

  主な実装は`backend/src/quicklook/coordinator/api/app.py`に行い、
  ユーザーからのリクエストは`backend/src/quicklook/frontend/api/app.py`に実装されたエンドポイントを通じて受け付け、それを`backend/src/quicklook/coordinator/api/app.py`のappに転送してください。
  coordinatorのエンドポイントは`/quicklooks/{visit_name}/vote`, `/quicklooks/{visit_name}/unvote`のような感じになるかと思います。（適宜調整をお願いします）

* [ ] 上記依頼のフロントエンド側の対応

  上記対応により、jobの対する`vote`, `unvote`ができるようになります。
  フロントエンドで適切なタイミングこれらのAPIを呼ぶようにしてください。
  `frontend/app/src/pages/Home/context/index.tsx`の`HomeContextProvider`の`currentQuicklook.id`が現在表示している`VisitName`に相当します。この値を監視し変更されるたびにvote, unvoteをして下さい。（変更前の値に対しunvote、変更後の値に対しvote）
  またページを閉じる時も現在表示中の`VisitName`に対してunvoteをしてください。これには`sendBeacon`を使うのが良いでしょう。
  実装の前に`npm run api:rtk-query`を実行して、API呼び出しのためのコードを生成してください。
