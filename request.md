## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [ ] k8sのliveness, readiness probeの設定

  `./k8s/helmchart/templates`の`db.yaml`, `coordinator.yaml`, `frontend.yaml`, `generator.yaml`にliveness, readiness probeの設定を追加する。最後の3者はこのアプリけーションで実装した各コンポーネントである。
  frontendは`{{Values.config.pathPrefix}}/api/healthz`、coordinatorは`/comm/healthz`、`/comm/healthz`が利用可能。

* [ ] vote, unvote周りのリファクタリング

  `backend/src/quicklook/coordinator/api/app.py`でrouteのパスに`{visit_name}`を使っている箇所は`Depends`を使ってください。
  `backend/src/quicklook/frontend/api/deps.py`が参考になります。
  coordinatorでは対応するjobがない場合は404を返すのではなく、特に何もせず終了するので良いです。

* [ ] `QuicklookMetadataProvider`のリファクタリング

  `frontend/app/src/pages/Home/context/quicklook.tsx`周辺のコードです。
  `QuicklookMetadataProvider`が長くなって見通しが悪いです。
  vote, unvoteに関する処理を1つのフックに切り出してそれを呼び出すようにしてください。

  引数の値が変わった時に登録されたコールバック関数を呼び出すフックを作りそれを使うようにしてください。
  次のようなシグネチャになると思います。
  ```typescript
  useWatch<T>(watchedValue: T, callback: (before: T, after: T) => void)
  ```

* [ ] `JobStatus`のエラー情報の追加

  `backend/src/quicklook/coordinator/create_quicklook/__init__.py`では`job.status.stage = 'error'`のように`JobStatus`にエラー状態にすることがある。`JobStatus`にエラー情報を保持するフィールドを追加しエラーが起きた時はエラー内容を保持させてください。

* [ ] ジョブのタイムアウト制限

  何らかの原因でquicklookの作成がいつまで経っても終わらないことがある（かもしれない）。
  `backend/src/quicklook/coordinator/create_quicklook/__init__.py`の`quicklook_pipeline`の各ステージに60秒（設定可能）のタイムアウトを設ける。新しくその目的のdecoratorをつくり各ステージの処理関数にそのデコレーターを作用させると良いだろう。
  タイムアウトを超えたら全てのgeneratorを再起動させる。`backend/src/quicklook/comm/coordinator.py`を参考。`shutdown_all_generators()`のような関数を作ると良いだろう。

* [ ] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`のリファクタリング

  * このコンポーネントで表示されるジョブのリストの上部が隠れて表示されていないようです。修正してください。
  * 現在表示しているvisitがまだリストにない時は`<LoadingSpinner/>`を表示してください。
  * quicklookがエラーステータスになったらエラーメッセージを表示してください。エラーメッセージの後に再リクエストボタンも配してください。
