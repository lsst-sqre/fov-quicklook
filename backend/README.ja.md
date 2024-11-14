### Frontend

* システムで複数実行
* asyncioで動く
* クライアントと通信
* API(クライアントに対するもの)

* [x] `GET /api/healthz`
  * 健康状態を返す
* [x] `GET /api/quicklooks/:id/status`
  * 指定されたquicklookの状態を返す
* [x] `GET /api/quicklooks/:id/status.ws`
  * 指定されたquicklookの状態を返す
* [x] `GET /api/quicklooks/:id/metadata`
  * 指定されたquicklookのメタデータを返す

### Coordinator

* システムでただ１つ実行される。
* asyncioで動く(シングルスレッド)
* quicklookの作成ジョブの管理
* API(Frontendに対するもの)
  * [x] `GET /healthz`
    * 健康状態を返す
  * [x] `POST /quicklooks`
    * quicklookの作成をリクエストする
    * このendpointはすぐ返る。処理の進捗は `GET /quicklooks/:id` で確認できる
  * [x] `DELETE /quicklooks/*`
    * 全てのquicklookの削除をリクエストする
    * テスト用
  * [x] `websocket /quicklooks/*/events.ws`
    * 全てのquicklookの状態をリアルタイムで得るためのAPI
  * [x] `POST /register_generator`
    * Generatorの登録をリクエストする
