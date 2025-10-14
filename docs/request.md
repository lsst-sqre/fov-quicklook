* こまめにgit commitしてください。

* `src/quicklook/coordinator/create_quicklook.py`の`_generate_single_fits_tiles_pipeline`について

  この関数は`_generate_single_fits_tiles`を置き換えることを目的として実装中でこれを完成させて欲しいです。
  `_generate_single_fits_tiles`と違うことは`generate_single_fits_tiles_pipeline`を使うところです。これはリモートの関数も`Iterabl[CcdDatRef]`を受け取り、内部でパイプライン処理を行います。

  `ccd_refs`を`workers`で分散して処理します。

  次のことを守り実装を完成させてください。
  * 1つのworkerには決まった数以上のCCDを同時に割り当てない。処理が終わったら別の`ccd_ref`を割り当てられるようになります。
  * 1つの`ccd_ref`の処理が終わると`CcdMetadata`が`generate_single_fits_tiles_pipeline`から返ってきます。
  * rpcからは`CcdMetadata`か`GenerateSingleFitsTilesProgress`が返ってきます。これを適切に処理してください。`_generate_single_fits_tiles`が参考になります。
  * 全部のccdをworkerにdispatchした後の処理
    * 遅いworkerに割り当てられた`ccd_ref`は処理の完了に非常に時間がかかってしまうことがある。それを見越して昔にdispatchして完了していない`ccd_ref`を再度空いているworkerにdispatchしてください。

* `src/quicklook/rpc/server.py`では`multiprocessing.Manager`を使っているが、
このmanagerが作ったqueueは複数のプロセスで共有されているわけではないので単に`multiprocessing.Queue`を使えば十分です。
そのように変更してmanagerに関するコードを削除してください。
