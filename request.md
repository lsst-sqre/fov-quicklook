## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。

* [x] `frontend/app/src/pages/Home/Viewer/CompactStatus/index.tsx`のリファクタリング

  現在のvisitに対応するハイライトを黄色ではなくテーマに沿った青緑系の色にしてください。

* [x] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`のリファクタリング

  `generate_single_fits_tiles`ステージの時`<GenerateSingleFitsTilesVisualizer/>`が表示されるはずなのに`<JobList/>`が表示されてしまいます。
  バックエンドも確認して原因を特定してください。

* [x] エラー対応

  coordinatorで`log-2.log`のエラーが起きています。
  対応をお願いします。

* [x] タイムアウトが効いていない？

  `backend/src/quicklook/coordinator/create_quicklook/__init__.py`のタイムアウト処理が失敗しているようです。
  見直してください。上記のエラーがが関係しているかもしれません。

* [x] エラーが起きて消えずに残っているエントリーがある。

  `backend/src/quicklook/coordinator/create_quicklook/__init__.py`でエラーのエントリーは消えるはずなのですが残っています。
  見直してください。上記のエラーがが関係しているかもしれません。
