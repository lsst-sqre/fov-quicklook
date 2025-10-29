## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [ ] `backend/src/quicklook/coordinator/api/app.py`

  vote, unvoteが行われたらログに現在のすべてのエントリーのvisit_name, user_countを出力するようにしてください。
  単にvote, unvote自体のログは不要です。

* [ ] `backend/src/quicklook/coordinator/create_quicklook/__init__.py`のリファクタリング

  `quicklook_pipeline`のなかの各ステージに対応する関数にタイムアウトに関する同じパターンが繰り返されています。
  `quicklook_pipeline`内にデコレーターや高階関数を作ることで整理してください。
  `backend/src/quicklook/coordinator/create_quicklook/pipeline_timeout.py`がどこからも使われていなければ削除してください。

* [ ] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。
