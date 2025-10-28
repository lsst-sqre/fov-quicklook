## 依頼

### 気をつけること

* こまめに`git commit`してください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [ ] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。

* [ ] `frontend/app/src/pages/Home/Viewer/CompactStatus/index.tsx`のリファクタリング

  * メモリ使用率やCPU使用率のバーにマウスオーバーをすると、値自体をツールチップで表示するようにしてください。
    例： 100MiB, 50%など

  * 現在は`frontend/app/src/pages/admin/Status/index.tsx`の`Unrecoverable Memory`に相当するものが表示されています。
    これに加えてただの`Memory Usage`に対応するものも表示できるようにしてください。
    ただし、その表示はデフォルトではオフで切り替えられるようにしてください。
    切り替えは`frontend/app/src/pages/Home/MainMenu/index.tsx`で行えるようにして下さい。

* [ ] `QuicklookMetadata`のリファクタリング

  `backend/src/quicklook/frontend/api/quicklooks.py`周辺のコードについてです。
  `type QuicklookMetadata = QuicklookMetadataReady | QuicklookMetadataProgress | QuicklookMetadataError`に新しく`QuicklookMetadataPending`を追加してください。
  ```python
  @dataclass
  class QuicklookMetadataPending:
      visit_name: VisitName
      type: Literal['pending'] = 'pending'
  ```
  これは`_get_quicklook_metadata_from_shared_status`では`job_status`が`None`の場合に返します。

* [ ] `frontend/app/src/pages/Home/Viewer/QuicklookJobMonitor.tsx`のリファクタリング

  `QuicklookMetadataPending`が帰ってきたら`metadata?.type === 'pending'`の時に`<JobList/>`を表示するようにしてください。
  また、そのように変更したら表示切り替えロジックを整理してください。現在すこしごちゃついています。

* [ ] `<Progress/>`のリファクタリング

  `frontend/app/src/components/Progress/index.tsx`のコンポーネントについてです。
  現在の実装だと進捗が極めて小さい時、進捗を示すバーの中の明るい部分がバーの背景部分を飛び出してしまいます。
  進捗を示す部分に`border-radius`を設定するのではなく、親要素（枠の要素）に`overflow: hidden`を設定するようにしてください。

* [ ] Cache entries表示のリファクタリング

  `frontend/app/src/pages/admin/CacheEntries/index.tsx`の現在の実装はエントリー1つ1つの容量の利用率が表示されています。
  そうではなく、全要素の合計のlimitに対する割合が画面全体で1つ、画面上部に表示されるようにしてください。
  これは`<Progress/>`要素を使うと良いでしょう。