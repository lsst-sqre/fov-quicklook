# 実装詳細

このドキュメントでは、`concept.ja.md`で説明された概念設計がどのように実装されているかを解説します。

## ディレクトリ構造

```
src/quicklook/
├── comm/           # コンポーネント間通信 (RPC, HTTP)
├── config/         # 設定管理 (Pydantic)
├── coordinator/    # Coordinator コンポーネントの実装
│   └── create_quicklook/ # パイプライン処理のロジック
├── datasource/     # データソース (Butler, Dummy)
├── db/             # データベースモデル (SQLAlchemy)
├── frontend/       # Frontend コンポーネントの実装
├── generator/      # Generator コンポーネントの実装 (各ステージの処理)
├── job/            # ジョブ管理
├── object_storage/ # オブジェクトストレージ操作
├── rpc/            # RPC フレームワーク
├── types.py        # 型定義
└── utils/          # ユーティリティ (Pipeline, Geometry など)
```

## コンポーネントの実装詳細

### Coordinator

Coordinatorはシステムの中心であり、ジョブのスケジューリングとパイプラインの実行を管理します。

*   **パイプライン (`src/quicklook/utils/pipeline/`)**:
    *   処理はステージの連なりとして定義されます。
    *   `src/quicklook/coordinator/create_quicklook/__init__.py` で `quicklook_pipeline` が定義されています。
    *   主なステージ: `generate_single_fits_tiles`, `merge_tiles`, `upload_to_object_storage`。

*   **動的ディスパッチ (`src/quicklook/coordinator/create_quicklook/generate_single_fits_tiles_coordinator.py`)**:
    *   `generate_single_fits_tiles` ステージでは、複数の Generator に処理を分散させます。
    *   `RpcQueue` を使用して、Generator からの完了通知を受け取るたびに新しいタスク (CCD) を供給する方式をとっています。これにより、処理速度の異なる Generator 間で負荷分散を行います。

### Generator

Generatorは実際のデータ処理を行うワーカーです。

*   **FITS処理 (`src/quicklook/generator/generate_single_fits_tiles.py`)**:
    *   FITSファイルを読み込み、タイル画像を生成します。
    *   生成されたタイルは一時的にローカルストレージ (`emptyDir` など) に保存されます。

*   **タイルマージ (`src/quicklook/generator/merge_single_tile_fits.py`)**:
    *   複数のFITSファイルにまたがるタイルを合成します。
    *   必要に応じて他の Generator から HTTP 経由で中間データを取得します。

*   **転送 (`src/quicklook/generator/transfer_tiles.py`)**:
    *   生成されたタイルを 4x4 のブロックにパッキングし、オブジェクトストレージにアップロードします。
    *   `PackedTilePos` を使用して管理します。

### Database

*   `src/quicklook/db/` に SQLAlchemy のモデル定義があります。
*   ジョブの状態や生成された Quicklook のメタデータを管理します。

### 通信 (RPC)

*   `src/quicklook/comm/` および `src/quicklook/rpc/` で実装されています。
*   Coordinator と Generator 間の通信は、HTTP ストリーミング上の RPC で行われます。
*   Python の `pickle` を使用して関数呼び出しと引数をシリアライズして送信します。

## 重要なモジュール

### Job (`src/quicklook/job/`)

*   パイプライン処理の単位である Job を表現します。
*   状態管理、ローカルストレージへのパス解決、ステータスの監視などの機能を提供します。

### Object Storage (`src/quicklook/object_storage/`)

*   S3 互換のオブジェクトストレージへのアクセスを抽象化しています。
*   タイルのアップロード、ダウンロード、メタデータの管理を行います。
*   LRU キャッシュ機能も実装されています。

### DataSource (`src/quicklook/datasource/`)

*   LSST のデータ管理システム (Butler) へのアクセスを抽象化しています。
*   テスト時には `DummyDataSource` を使用することで、Butler なしで動作確認が可能です。
