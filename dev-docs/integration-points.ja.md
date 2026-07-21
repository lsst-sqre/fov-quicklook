# クリティカルな統合ポイント

このドキュメントは FOV-Quicklook システムのコンポーネント間通信について詳細に説明します。

## フロントエンド ↔ コーディネーター (REST API)

**ベース URL**: `QUICKLOOK_coordinator_base_url` で設定 (デフォルト: `http://localhost:9501`)

**主要なエンドポイント**:
- `POST /api/quicklooks` — 観測のタイル生成をリクエスト
- `GET /api/quicklooks/{id}` — ジョブ状態とメタデータを確認
- `GET /api/tiles/{z}/{x}/{y}` — タイル取得 (S3 キャッシュから)
- `GET /pod_status` — システムヘルス (ジェネレーター統計を集約)
- `GET /healthz` — ライブネスチェック (登録済みジェネレーターリストを返す)

**実装**: `backend/src/quicklook/coordinator/api/` (FastAPI ルーター)

**フロントエンドからのアクセス**: `frontend/app/src/store/api/openapi.ts` (OpenAPI スキーマから自動生成された RTK Query フック)

## コーディネーター ↔ ジェネレーター (HTTP 上の RPC)

**ディスカバリープロトコル**:
1. 各ジェネレーターが定期的に `POST /register_generator` でその `{host, port}` を送信
2. コーディネーターがインメモリリストを保持し、`config.heartbeat_interval` 秒ごとに `GET /healthz` でヘルスチェック
3. 到達不可能なジェネレーターは自動削除

**タスクディスパッチ** (同期 HTTP ストリーミング):
- コーディネーター: `POST http://{generator}:{port}/quicklooks` で `GenerateTask` ペイロードを発行
- レスポンス: ストリーミング JSON 進捗メッセージ、その後最終結果
- パース: `message_from_async_reader()` ユーティリティがストリームされたオブジェクトを解凍

**タスクタイプ** (`backend/src/quicklook/coordinator/quicklookjob/tasks.py` で定義):
- `GenerateTask`: どの CCD をタイル化するか、どのジェネレーターが処理するか
- `MergeTask`: どのタイルをマージするか (`ccd_generator_map` がプロデューサーを追跡)
- `TransferTask`: どのパック済みタイルを圧縮・アップロードするか

**重要な不変条件**: RPC ハンドラー関数は **両方** のコーディネーターとジェネレーターモジュールからインポート可能でなければなりません (共有インポートパス、例: `quicklook.generator.api.tilegenerate.run_generate`)。

## データフロー: データソース → ジェネレーター → オブジェクトストレージ

**データソース抽象化** (`backend/src/quicklook/datasource/types.py`):
- **本番環境**: `ButlerDataSource` (LSST Butler 経由で FITS を取得)
- **テスト**: `DummyDataSource` (合成データ、Butler 依存性なし)
- **注入**: `get_datasource()` ファクトリー関数 (`config.data_source` 環境変数で制御)

**中間ストレージ** (ジェネレーターローカル):
- パス: `config.job_local_dir` (通常は `/tmp` または k8s 一時 `emptyDir`)
- フォーマット: 個別 `.npy` タイル (バイナリ numpy 配列)
- ライフサイクル: GenerateSingleFitsTiles 中に作成、MergeSingleFitsTiles 後に削除

**最終ストレージ** (オブジェクトストレージ、S3 互換):
- **設定**: `QUICKLOOK_s3_tile` 環境変数 (JSON: `{access_key, secret_key, endpoint, bucket, ...}`)
- **キーパターン**: `quicklooks/{visit}/packed-tile/{level}/{i}/{j}.npy.zstd.list.pickle`
- **フォーマット**: 16個のタイル numpy 配列のピクル化リスト (4×4 グループ、zstd で圧縮)
- **アクセス**: `backend/src/quicklook/object_storage/` モジュールがキャッシュレイヤーを提供 (LRU キャッシュ)
- **サイズ**: 単一タイル ~100-200KB、パック済み 4×4 ~1.6-3.2MB
