このモジュール `src/quicklook/rpc` について追加の依頼があります。
`./README.ja.md`の内容を参照してください。

以下のタスクを完了させてください。こまめに`git commit`してください。

* 現在の`./client.py`の実装を見るとサーバーが非同期に`YieldMessage`を送ってきても呼び出し側はそれを配列に格納するだけで即座に`yield`していませんね？
これではリアルタイム性が損なわれてしまいます。`YieldMessage`は即座に呼び出し側でも`yield`するようにしてください。

* `./client.py`のRpcの型ですが、`Generic`にしていないですね、`run`メソッドを読んだときに結果の型がちゃんと推論されていますか？
`@overload`を使って`func`の戻り値の型によって`Awaitable`を返すか`AsyncGenerator`を返すかも切り替えて欲しいです。
ここは`make pyright`で
  
* `./server.py`で`if hasattr(arg, "__class__") and arg.__class__.__name__ == "_RpcQueue":`のようなことをしているコードがありますが、
`isinstance`を使うようにしてください。
`isinstance`を使うようにしてください。

* `./server.py`の型が曖昧な箇所が多いですね。`manager.Queue`などは`queue.Queue`にタイプキャストして良いでしょう。
また`./server.py`のプロセス間通信は`tuple`ではなく`dataclass`で定義されたインスタンスを送り合うのが良いでしょう。

* `./client.py`, `./server.py`で`args`, `kwargs`で同じ処理を繰り返し書いている場所があります。別関数にするなどして重複の記述をやめてください。

* `src/comm/rpc.py`の置き換え
  * コードベース内で`src/comm/rpc.py`のRpcを使っている箇所を探してこのモジュール(`src/quicklook/rpc`)を使ったものに置き換えてください。
