## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [ ] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。

* [ ] `backend/src/quicklook/utils/timeout.py`の移動。

  このファイルの内容は`utils`内にあるのは相応しくないですね。（汎用的でない。）
  `backend/src/quicklook/coordinator/create_quicklook`に移動させてください。
  名前ももう少し具体的にしましょう。

* [ ] キャッシュ一覧からquicklookを閲覧可能にする

  `frontend/app/src/pages/admin/CacheEntries/index.tsx`でキャッシュデータの一覧が見える。
  visit nameをクリックするとそのデータが見えるようにする。(`src/router.tsx`参照。`/visits/:visitId`に飛ばす。)

* [ ] ジョブ一覧ページからもquicklookを閲覧可能にする

  上記依頼と同様`frontend/app/src/components/JobStatusVisualizer/JobStatusVisualizer.tsx`からquicklook閲覧ページをリンクする。

* [ ] システムステータスの改善

  * 表示

    `frontend/app/src/pages/admin/Status/index.tsx`にステータス表示のコードがあります。
    これは画面全体を使って表示するものですが、`<Home />`画面の端に表示できると良いです。
    そのための小型版も作って`<Home/>`内の`<Viewer/>`枠の左下に小型版を表示するようにしてください。
    小型版は各コンテナの名前、Unrecoverable Memory、CPU Usageだけ表示してください。
    メモリ、CPUは`<Progress />`でバーで表示してください。
    コンテナ名かなり長くなるのでcoordinatorは`coordinator`、frontendは`frontend`、generatorは先頭の6文字だけを表示してください。

  * 無駄の削減

    現在、クライアントからリクエストがあると`backend/src/quicklook/frontend/api/status.py`のAPIが呼ばれてそこからcoordinator, generatorへとリクエストがリレーされていきます。これが複数のクライアントから来ると無視できないトラフィックになります。
    frontendでは結果を`backend/src/quicklook/utils/ttlcache/__init__.py`を使って１秒間キャッシュし何度もバックエンドにリクエストをしないようにしてください。
    また`backend/src/quicklook/frontend/api/status.py`にwebsocketのエンドポイントも作って、クライアントのとのやりとりはそれを使うようにしましょう。
    クライアントサイドがwebsocketと通信するには`frontend/app/src/store/api/base.ts`に新しくエンドポイントを追加してください。既存のコードがwebsocketの使いかたの参考になります。
    バックエンド側にwebsocketでない通常のAPIは残しておいてください。（これを残しておくとOpenAPIの型情報がクライアントで利用できる。）

* [ ] アクセス記録の作成

  現在`backend/src/quicklook/coordinator/housekeeping/__init__.py`で古いキャッシュを削除している。
  １週間以内の`accesses`テーブルのエントリー数が少ないものから順に消しています。
  しかし、現在アクセス時に`accesses`テーブルのレコードを作る処理がありません。
  `backend/src/quicklook/frontend/api/quicklooks.py`の`vote`された時に`accesses`テーブルにレコードを作成する処理を追加するようにしてください。

* [ ] フロントエンドのジョブ表示の問題

  `src/pages/Home/Viewer/QuicklookJobMonitor.tsx`周辺についてです。
  `<LoadingSpinner/>`は表示領域の中央に表示してください。
  リストが表示された時、自分の今見ているvisitに対応するジョブを画面中央にスクロールさせてください。

* [ ] DBのyamlファイルの見直し

  `k8s/helmchart/templates/db.yaml`が作るdeploymentがrestartできません。
  （ずっと古いpodが残り続けます。）
  可能なら修正してください。
  （これは別のリポジトリにあります。cdするときはこのタスクが終わった時のcurrent directoryには注意してください。）

* [ ] キャッシュエントリーにキャッシュの使用量を表示する。

  `frontend/app/src/pages/admin/CacheEntries/index.tsx`にキャッシュの一覧が表示されているが、
  これにキャッシュの使用量のlimitの何%が使われているか表示するようにしてください。
  上限値は`backend/src/quicklook/config/__init__.py`の`max_object_storage_usage`です。
  この値を`backend/src/quicklook/frontend/api/systeminfo.py`経由でクライアントに渡すと良いでしょう。

* [ ] ミニシステムモニターの表示修正

  `frontend/app/src/pages/Home/Viewer/index.tsx`の`CompactStatus`のCPU使用率の値がおかしい？
  サーバーサイドの実装`backend/src/quicklook/utils/system_status.py`とも見比べてCPU使用率がlimitに達した時に100%になるように修正してください。

  あと、`frontend/app/src/pages/Home/MainMenu/index.tsx`の`<MainMenu/>`にミニシステムモニターの表示非表示の項目の切り替え項目を作ってください。