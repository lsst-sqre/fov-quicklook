* こまめにgit commitしてください。
* まずこのファイルにtodo一覧を作ってください。
  * 例えばコードツリーに対するレビューならば対象コードのリストを作る。
  * ここでまずcommit
  * todoを1つずつこなし、チェックをしてタスクを進めてください。

* [ ] ./src以下のコードの次の観点でレビューしてください。
  * デッドロックが発生しないか
    * 正常系では問題なく動作することは確認済みですが、思わぬところで例外が起きた時にデッドロックに陥らないか
  * リソースリークが発生しないか
    * 解放し忘れのリソースがないか
    * Generatorを途中でexitした場合、generatorが必ず解放されるか
      * `contextmanager.closing`を積極的に使用しても良いだろう。

## レビュー対象ファイルリスト

### 高優先度（非同期処理・リソース管理が複雑）
- [ ] `src/quicklook/rpc/` - RPC通信（クライアント・サーバー・キュー）
  - [ ] `rpc/client.py` - RPCクライアント
  - [ ] `rpc/server.py` - RPCサーバー
  - [ ] `rpc/queue.py` - 非同期キュー
  - [ ] `rpc/lifespan.py` - ライフサイクル管理
- [ ] `src/quicklook/coordinator/` - Coordinatorプロセス
  - [ ] `coordinator/app.py` - アプリケーション
  - [ ] `coordinator/coordinator.py` - コーディネーター本体
  - [ ] `coordinator/rpc_worker.py` - RPCワーカー
  - [ ] `coordinator/request_queue.py` - リクエストキュー
  - [ ] `coordinator/create_quicklook.py` - quicklook作成
- [ ] `src/quicklook/generator/` - Generatorプロセス
  - [ ] `generator/app.py` - アプリケーション
  - [ ] `generator/generator.py` - ジェネレーター本体
  - [ ] `generator/rpc_worker.py` - RPCワーカー
  - [ ] `generator/quicklook.py` - quicklook処理
- [ ] `src/quicklook/job/` - ジョブ管理
  - [ ] `job/__init__.py` - ジョブクラス
  - [ ] `job/localstorage.py` - ローカルストレージ
  - [ ] `job/storage.py` - ストレージ抽象化
- [ ] `src/quicklook/comm/` - 通信レイヤー
  - [ ] `comm/__init__.py` - 通信ユーティリティ

### 中優先度（並行処理あり）
- [ ] `src/quicklook/utils/` - ユーティリティ
  - [ ] `utils/adaptive_map/` - 適応的マッピング
  - [ ] `utils/pipeline/` - パイプライン処理
  - [ ] `utils/async_generator_pipe.py` - 非同期ジェネレータパイプ
- [ ] `src/quicklook/frontend/` - フロントエンドAPI
  - [ ] `frontend/api/` - APIエンドポイント
- [ ] `src/quicklook/db/` - データベース
  - [ ] `db/__init__.py` - セッション管理
- [ ] `src/quicklook/object_storage/` - オブジェクトストレージ

### 低優先度（I/O中心、同期処理）
- [ ] `src/quicklook/datasource/` - データソース
- [ ] `src/quicklook/tileinfo/` - タイル情報
- [ ] `src/quicklook/config/` - 設定
- [ ] `src/quicklook/types.py` - 型定義

