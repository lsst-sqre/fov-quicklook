# 未完タスク

* [ ] `src/quicklook/coordinator/test_create_quicklook.py`のリファクタリング
  * このモジュールのテストの開始時に`quicklooks`テーブルの状態をリセットする。
  * `./.venv/bin/pytest src/quicklook/coordinator/test_create_quicklook.py -m 'slow'` でテスト実施
* [ ] `./src/quicklook/comm`周辺のリファクタリング
  * coordinatorはエラー時にcoordinator_idをエラー通知に含めない
* [ ] `./src/quicklook/coordinator/create_quicklook.py`周辺のリファクタリング
  * `_finalize`は必ず`error=True`で呼び出されているので`_finalize_error`という名前に変更し、`error`パラメーターを削除
  * `JobStatus.stage`に`error`ステータスを追加する。
    * エラー時はステータスを`error`にする
    * `src/quicklook/coordinator/api/app.py`ではエラー時はすぐに`jobs`から削除するのではなく30秒経過してから削除する
  * `_transfer_fits_headers`は`_merge_tiles`などと同列にpipelineのステージとして扱う。
    * `_transfer_fits_headers`の`uploaded_size`も`transfer_tiles`の`uploaded_size`と合算してDBのエントリーの情報に記録する。
  * `./.venv/bin/pytest src/quicklook/coordinator/test_create_quicklook.py -m 'slow'` でテスト実施
* [ ] `./src/quicklook/object_storage/__init__.py`周辺のリファクタリング
  * `VisitObjectStorage`にasync版のメソッドを追加する。
    * s3関係のメソッドは同期関数なので時間がかかる場合はasync環境で実行すると全体をブロックしてしまう。そのため、async版のメソッドを追加し、非同期で実行できるようにする必要がある。
  * 既存のオブジェクトストレージにアクセスするsync版のメソッドはメソッド名の末尾に`_sync`をつけたものにrenameする。
  * async版はsync版を別スレッドで動かす。
  * 既存メソッドの呼び出し元を探しasync環境で呼び出されているものはasync版に置き換える
* [ ] `./src/quicklook/config/__init__.py`周りのリファクタリング
  * `max_object_storage_usage`のデフォルト値を45GBに変更
* [ ] `./src/quicklook/coordinator/housekeeping/__init__.py`周辺のリファクタリング
  * テストコードを作成
    * テスト開始時にDBを全てリセットしても良い

# 完了タスク

* [x] commのリファクタリング
  * `./src/quicklook/comm`にcoordinatorとgeneratorの連携の処理がある。
  * 現在、generatorからcoordinatorへ定期的に自身の登録処理を行っているが、これに処理を加える。
  * coordinatorは起動時にuuidを自身に割り当てる
  * generatorは初回の登録時にそのuuidをcoordinatorから受け取る
  * generatorは定期的な登録時にそのuuidをcoordinatorに送信する。
  * coordinatorはそのuuidが自身のuuidと違ったら登録を拒否(これはcoordinatorが再起動したことを意味する。)
  * generatorはこの場合、シャットダウンする（`_shutdown`関数を使う）
* DB関係
  * 開発環境
    * `make db/docker` で開発用DBが起動する。
    * DBへの接続情報は`src/quicklook/config/__init__.py`に記述する。
  * [x] async版のSQLAlchemy2を導入
    * スキーマは下記参照
  * [x] alembic導入
    * `Makefile`の`db/*`でalembicに関するタスクを管理できるようにする。
* DBへのquicklookの情報を登録する
  * [ ] `src/quicklook/coordinator/create_quicklook.py`を実装する。
    * quicklookの作成初期に`ready=false`のレコードを作成, 完了時に`ready=true`にする。`disk_usage`もこの時に設定する。
    * エラーが起きた場合、レコードを削除する。
      * `_finalize`関数に`error`パラメーターを追加し、そこで処理するのが良いだろう。
* [x] `src/quicklook/coordinator/create_quicklook.py`への処理追加
  * `_finalize`でエラー時にはobject storageのデータも削除するようにする。
    * `job.object_storage`を参考にする。
    * 現状object storageの関連するエントリーを削除するメソッドは`VisitObjectStorage`にはない。`delete_objects_by_prefix`を利用したメソッドを実装する必要があるだろう。
* [x] housekeeping
  * 現状では`quicklooks`レコードは次々に増えていき、同時にobject storageにもデータが蓄積されていく
  * あるタイミングでデータを選んで削除する必要がある。これを行う`async`関数を以下のように実装する。
    * `src/quicklook/config/__init__.py`にobject storageの利用量上限の設定を設ける
    * 現在のobject storageの利用量はDBの`sum(quicklooks.disk_usage)`で確認できる。
    * 実装するファイルは`src/quicklook/coordinator/housekeeping/__init__.py`
    * この関数を呼ばれると次のような処理を行う
      * 1つ削除すべき`quicklooks`のエントリーを選ぶ
        * このエントリーを選ぶ関数は別に分ける
        * とりあえず、最近１週間以内のアクセスが少ないもの順、（それが同じなら`created_at`が古いもの順）で1つ選ぶ
      * `ready=false`にする
      * そのエントリーに関連するobject storageのデータを削除する。
      * object storageのデータの削除が終わったらDBのエントリーを削除する。
      * `disk_usage`の合計が設定値より小さくなるまで繰り返す。
      * エントリーを1つ削除する関数を別に分けるのが良いだろう
    * object storageの大量のエントリーの削除はおそらく時間がかかる。それを含む関数はsync版を作りasyncではそれを別スレッドで動かす必要があるだろう
* [x] 起動時のcleaning up
  * `src/quicklook/coordinator/housekeeping/__init__.py`にそのための関数を実装する。
  * この関数は`ready=false`の`quicklooks`のエントリーがあれば、関連するデータを削除しそれが完了したらDBのエントリーを削除する。
  * 上述のhousekeepingの中で整備した関数が利用できるだろう
* [x] DBのbootstrap用スクリプトの準備
  * alembicのマイグレーションを実行するスクリプトを作成する。
  * これに失敗したらDB内のテーブルを全て削除し、object storage内の`config.s3_tile_key_prefix`から始まるオブジェクトを全て削除して再度マイグレーションを実行
* [x] `JobStatus`に`src/quicklook/coordinator/create_quicklook.py`の`ccd_generator_map`を保持させる。
* [x] fits_header、メタデータのobject storageへのアップロード機能（`transfer_metadata`）の実装
  * `generate_single_fits_tiles`, `merge_fits_tiles`, `transfer_fits_tiles`に並ぶタスクとして実装する。
  * `merge_fits_tiles`の後に行う
  * fits headerは各CCDにつき１つ得られる。
  * `src/quicklook/generator/generate_single_fits_tiles.py`の`job.local_storage.fits_header.save(ref, ppccd.headers)`でローカルストレージに保存されている。
  * これを`src/quicklook/generator/merge_single_tile_fits.py`の`_iter_primary_pos(job: Job)`を参考に自ノードで処理したものに関して`job.object_storage`を通じてobject storageへアップロードする。なお、`VisitObjectStorage`に新たにfits headerをアップロードするためのメソッドを追加する必要がある。
  * アップロードした合計を呼び出し元に返す。
* [x] quicklook metadataのオブジェクトストレージへの保存
  * `src/quicklook/coordinator/create_quicklook.py`の`_generate_single_fits_tiles`で各CCDのメタデータが集められる。
  * このリストをobject storageに保存する。

## DBスキーマ

```sql
create table quicklooks ( 
  visit_name: string primary key,
  job_id: string not null unique,
  disk_usage: integer not null,
  created_at: datetime not null
);

create table accesses (
  visit_name: string references quicklooks(visit_name),
  accessed_at: datetime not null
);
```
