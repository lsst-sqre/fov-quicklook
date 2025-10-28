## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。

* [x] キャッシュエントリーにキャッシュの使用量を表示する。

  `frontend/app/src/pages/admin/CacheEntries/index.tsx`にキャッシュの一覧が表示されているが、
  これにキャッシュの使用量のlimitの何%が使われているか表示するようにしてください。
  上限値は`backend/src/quicklook/config/__init__.py`の`max_object_storage_usage`です。
  この値を`backend/src/quicklook/frontend/api/systeminfo.py`経由でクライアントに渡すと良いでしょう。

* [x] ミニシステムモニターの表示修正

  `frontend/app/src/pages/Home/Viewer/index.tsx`の`CompactStatus`のCPU使用率の値がおかしい？
  サーバーサイドの実装`backend/src/quicklook/utils/system_status.py`とも見比べてCPU使用率がlimitに達した時に100%になるように修正してください。

  あと、`frontend/app/src/pages/Home/MainMenu/index.tsx`の`<MainMenu/>`にミニシステムモニターの表示非表示の項目の切り替え項目を作ってください。

* [ ] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`のリファクタリング

  現在、`Object.keys(metadata.progress).length`を条件の1つとして

  リストではなく1visit分の`<GenerateSingleFitsTilesVisualizer />`を表示する時は表示領域の中央に表示するようにしてください。
