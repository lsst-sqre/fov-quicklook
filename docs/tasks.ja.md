# 残りタスク

* DB関係
  * 開発環境
    * `make db/docker` で開発用DBが起動する。
    * DBへの接続情報は`src/quicklook/config/__init__.py`に記述する。
  * [ ] async版のSQLAlchemy2を導入
    * スキーマは下記参照
  * [ ] alembic導入
    * `Makefile`の`db/*`でalembicに関するタスクを管理できるようにする。
* DBへのquicklookの情報を登録する
  * [ ] `src/quicklook/coordinator/create_quicklook.py`を実装する。
    * quicklookの作成初期に`ready=false`のレコードを作成, 完了時に`ready=true`にする。`disk_usage`もこの時に設定する。
    * エラーが起きた場合、レコードを削除する。
      * `_finalize`関数に`error`パラメーターを追加し、そこで処理するのが良いだろう。
* [ ] `src/quicklook/coordinator/create_quicklook.py`への処理追加
  * `_finalize`でエラー時にはobject storageのデータも削除するようにする。
    * `job.object_storage`を参考にする。
    * 現状object storageの関連するエントリーを削除するメソッドは`VisitObjectStorage`にはない。`delete_objects_by_prefix`を利用したメソッドを実装する必要があるだろう。
* [ ] housekeeping
  * 現状では`quicklooks`レコードは次々に増えていき、同時にobject storageにもデータが蓄積されていく
  * あるタイミングでデータを選んで削除する必要がある。これを行う`async`関数を以下のように実装する。
    * `src/quicklook/config/__init__.py`にobject storageの利用量上限の設定を設ける
    * 現在のobject storageの利用量はDBの`sum(quicklooks.disk_usage)`で確認できる。
    * 実装するファイルは`src/quicklook/coordinator/housekeeping/__init__.py`
    * この関数を呼ばれると次のような処理を行う
      * 1つ削除すべき`quicklooks`のエントリーを選ぶ
        * このエントリーを選ぶ関数は別に分ける
        * とりあえず、最近１週間以内のアクセスが少ないもの順、（それが同じなら`created_at`が古いもの順）で1つ選ぶ
      * `deleting`にエントリーを追加する。
      * そのエントリーに関連するobject storageのデータを削除する。
      * object storageのデータの削除が終わったらDBのエントリーを削除する。
      * `disk_usage`の合計が設定値より小さくなるまで繰り返す。
* [ ] quicklook metadata整備

* [ ] 起動時のcleaning up
  * `src/quicklook/coordinator/housekeeping/__init__.py`にそのための関数を実装する。
  * この関数は`ready=false`の`quicklooks`のエントリーがあれば、関連するデータを削除しそれが完了したらDBのエントリーを削除する。
* [ ] DBのbootstrap用スクリプトの準備
  * alembicのマイグレーションを実行するスクリプトを作成する。
  * これに失敗したらDB内のテーブルを全て削除し、object storage内の`config.s3_tile_key_prefix`から始まるオブジェクトを全て削除して再度マイグレーションを実行

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

create table deleting (
  visit_name: string primary key references quicklooks(visit_name),
  created_at: datetime not null
)
```
