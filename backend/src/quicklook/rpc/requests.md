このモジュール `src/quicklook/rpc` について追加の依頼があります。
`./README.ja.md`の内容を参照してください。

以下のタスクを完了させてください。こまめに`git commit`してください。

* commit `8552a0f`の取消。この変更は必要ありませんでした。元に戻してください。

* `./test_rpc.py`の`async for item in await Rpc(rpc_server, queue_generator_function, RpcQueue(client_queue)).run():`で型エラーが出ています。ここはこのようにgeneratorをiterateする場合は別の関数にするのでも良いです。（実行時にgeneratorでないものにiterateしていたらエラーを出す）
`# type: ignore`を使わないでちゃんと型推論がされるようにして下さい。

    ```python
    async for item in Rpc(rpc_server, queue_generator_function, RpcQueue(client_queue)).iterate():
        ...
    ```

* 先の依頼で`quicklook/comm/rpc.py`のコードを削除しこのモジュールを使うようにしてもらいました。(`d9b0e6eb2e6d97f020d9eda82d35af4acd3f3ff1`)
その際テストが一部壊れてしまいました。`make test/all`でエラーが出ないようにしてください。
