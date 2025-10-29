## 依頼

### 気をつけること

* こまめに`git commit`してください。
  * 最低でも１項目に１回はcommitしてください。
* 以下の依頼を完了したらチェックボックスに記しを入れてください。

以下を順に実施してください。

* [x] `backend/src/quicklook/coordinator/api/app.py`の見直し

  vote時にselectしているが、selectした後に対応するQuicklookエントリが消える可能性はない？
  もしトランザクションの関係でその心配がないならこのままで良いです。

  特に理由がなければ`import`類はファイルの先頭にまとめましょう

* [x] `pyright`の実行と修正

  `cd backend && make pyright` してエラーがあれば修正してください。
