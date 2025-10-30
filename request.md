## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `backend/src/quicklook/coordinator/housekeeping/__init__.py:select_quicklook_to_delete`のリファクタリング

    現在の実装はアクセス頻度の高いものは消えないことになっている。
    しかしこれでは、キャッシュにアクセス頻度が高いものだけ残ってしまった時に新しいデータが追加されなくなってしまう。
    アクセス頻度が高いものと新しいもののバランスを取る必要がある。
    10(設定可能の値)エントリー分はアクセス頻度と関係なく新しいものを残すように変更してください。

* [x] `frontend/app/src/pages/Home/Viewer/index.tsx`の`<QuicklookJobMonitor/>`の見直し

    `<QuicklookJobMonitor/>`が`<JobList/>`を表示している時やリストが長いと最上部までスクロールできません。
    これは`scrollIntoView`の問題ではないです。マウスホイールでも最上部までスクロールできません。
    `<QuicklookJobMonitor/>`はアプリ全体でここでしか使われていません。親要素も検証し、問題を特定・修正してください。

