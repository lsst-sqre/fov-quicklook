このモジュール `src/quicklook/rpc` について追加の依頼があります。
`./README.ja.md`の内容を参照してください。

以下のタスクを完了させてください。こまめに`git commit`してください。

* `server.py`の`_process_args_kwargs_with_queue_map`, `_extract_rpc_queues`に重大なバグがあります。
`if isinstance(arg, int) and arg in queue_map:`というコードがありますが、これだと単にクライアントの呼び出し時にqueueとは無関係の整数の引数が与えられたときに誤ってキューとして扱われてしまうことがあります。修正してください。`_extract_rpc_queues`で整数値に置き換えるのではなく、queue idを持つ独自のdataclassに置き換えたりするのが良いでしょう。

* `_RpcQueue`の`queued_id`は値自体は重複さえしなければ良くて特に意味のある値ではないので、コンストラクタで通し番号を自動で降れば良いでしょう。
そうすれば`_get_next_queue_id`などは必要なく、`server.py`でもこの値が設定されているか調べる必要もなくなります。

* `client.py`, `server.py`で次の箇所で重複があります。これらの処理は共通化した方が良いでしょう。

  ```python
  # client.pyで
  if isinstance(v, _RpcQueue):
      queue_id = _get_next_queue_id()
      v.queue_id = queue_id
      processed_kwargs[k] = v
      queue_tasks.append(
          asyncio.create_task(_send_queue_messages_helper(ws, queue_id, v.queue))
      )
  ```

  ```python
  # server.pyで
  if isinstance(v, _RpcQueue):
    queue_id = v.queue_id
    assert queue_id is not None, "queue_id must be set by client"
    pipe: "queue.Queue[Any]" = manager.Queue()  # type: ignore[attr-defined]
    queue_map[queue_id] = pipe
    processed_kwargs[k] = queue_id
    queue_tasks.append(
        asyncio.create_task(_handle_queue_messages(ws, queue_id, pipe))
    )
    ```

* `./server.py`の`_QueueProxy`はGenericにしてqueueが保持する値の型を指定すると良いでしょう。

* `./test_rpc.py`の`async for item in await Rpc(rpc_server, queue_generator_function, RpcQueue(client_queue)).run():`で型エラーが出ています。修正してください。

* `quicklook/comm/rpc.py`とこのモジュールは内容が重複しています。
コードベース内で`quicklook/comm/rpc.py`を使っている箇所を探してこのモジュール(`src/quicklook/rpc`)を使ったものに置き換えてください。
その後`quicklook/comm/rpc.py`は削除してください。
