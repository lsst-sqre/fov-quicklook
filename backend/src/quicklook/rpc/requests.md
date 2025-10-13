このモジュール `src/quicklook/rpc` について追加の依頼があります。
`./README.ja.md`の内容を参照してください。

以下のタスクを完了させてください。こまめに`git commit`してください。

* 先の依頼で`quicklook/comm/rpc.py`のコードを削除しこのモジュールを使うようにしてもらいました。(`d9b0e6eb2e6d97f020d9eda82d35af4acd3f3ff1`)
その際テストが一部壊れてしまいました。` ./.venv/bin/pytest ./src/quicklook/coordinator/create_quicklook.py -m 'slow or not slow'` でエラーが出ないようにしてください。

adaptive_mapのテストが落ちる場合はそれらのテストを無効化して良いです。それらは近いうちに削除する予定のコードです。