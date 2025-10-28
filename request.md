## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] エラー修正

  coordinatorの起動直後に`./error.log`のようなエラーが出ます。
  修正してください。

* [x] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。

* [x] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`のリファクタリング

  `<QuicklookJobMonitor/>`の内容は表示領域の中央に表示するようにしてください。
  リスト表示をする時に待ち受け中のvisitに対応するjobのハイライトをもっと目立つ色にしてください。
  `<GenerateSingleFitsTilesVisualizer/>`は`Object.keys(tiles).length === 0`の間は`<GenerateSingleFitsTilesVisualizer/>`の上に`<LoadingSpinner/>`を被せるように表示してください。