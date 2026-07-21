# システム構成

FOV-Quicklook は、LSST Cam の 1 visit 分の大量 FITS を数秒でプレビュー可能なタイルへ変換し、
必要に応じて object storage へキャッシュする Kubernetes 前提のアプリケーションである。

## コンポーネント

| コンポーネント | 役割 | スケール |
|---|---|---|
| `frontend` | ブラウザ向けの入口。SPA 配信、REST / WebSocket API、タイル取得を担当 | 複数 pod |
| `coordinator` | ジョブ管理、generator の発見、動的ディスパッチ | 単一 pod |
| `generator` | FITS 読み出し、タイル生成、マージ、圧縮、アップロード | 複数 pod |
| PostgreSQL | ジョブ状態と復旧に必要な永続状態 | 単一 |
| S3 / MinIO | 生成済み PackedTiles と補助データの保管 | 共有 |

ブラウザから見た大きな流れは `Browser -> frontend -> coordinator -> generator -> S3`。

## データフロー

1. ブラウザが `frontend` に visit 一覧取得や quicklook 生成を要求する。
2. `frontend` は `coordinator` へジョブを渡し、進捗は WebSocket / API で返す。
3. `coordinator` は登録済み `generator` にタスクを分配する。
4. `generator` は中間タイルをローカルに作り、最終的に PackedTiles を object storage へ置く。
5. 以後の表示は `frontend` が object storage 上のタイルを返す。

## タイル生成パイプライン

quicklook は `(visit, data_type)` 単位で処理する。処理は 3 段階に分かれる。

| フェーズ | 内容 | 完了時の状態 |
|---|---|---|
| `GenerateSingleFitsTiles` | FITS を個別タイルへ変換 | プレビュー表示可能 |
| `MergeSingleFitsTiles` | generator 間でタイルを集約し重なりをマージ | CCD 境界をまたぐ表示が揃う |
| `TransferPackedTiles` | 4x4 単位で圧縮し object storage へ保存 | キャッシュ完了 |

4x4 でまとめるのは object 数を抑えるため。単一タイルは小さすぎ、S3 側の負荷が先に効く。

## コンポーネント間の通信

| 経路 | 方式 | 用途 |
|---|---|---|
| Browser -> frontend | HTTP / WebSocket | visit 一覧、quicklook 要求、進捗、タイル取得 |
| frontend -> coordinator | HTTP | ジョブ作成、状態照会、ヘルス確認 |
| generator -> coordinator | HTTP | heartbeat / register |
| coordinator -> generator | HTTP streaming RPC | generate / merge / transfer タスク実行 |
| generator -> S3 | S3 API | PackedTiles 保存 |

generator の性能は均一ではない前提なので、coordinator は固定割り当てではなく動的にタスクを配る。

## 状態の置き場所

| 置き場所 | 何を持つか |
|---|---|
| coordinator メモリ | 実行中ジョブ、generator の一覧、短命なスケジューリング状態 |
| PostgreSQL | 再起動後に復旧や掃除が必要なジョブ状態 |
| generator ローカル (`emptyDir`) | 中間タイル、一時生成物 |
| S3 / MinIO | 完成済み PackedTiles、必要に応じて test data |

generator は OOM や再起動で消える前提なので、復旧に必要な状態を generator メモリへ持たせない。

## 開発と運用の前提

- 開発は `/dev-docs/dev.ja.md` の microk8s dev pod を前提にする
- review app CI は `/dev-docs/ci.ja.md` の使い捨て namespace で動かす
- デプロイは `/dev-docs/phalanx.ja.md` の broker / ArgoCD 経路を使う
- Butler / Data Query の詳細は `/dev-docs/features/butler-data-query.ja.md` を参照する
