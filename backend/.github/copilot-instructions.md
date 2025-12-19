# FOV-Quicklook バックエンド向け Copilot 指示

## 概要

このドキュメントはバックエンド（Python）開発に特化した指示です。
プロジェクト全体の概要は `/.github/copilot-instructions.md` を参照してください。

---

## アーキテクチャ概要

詳細は `/docs/concept.ja.md` を参照してください。

**主要コンポーネント**:
- **Coordinator** (`src/quicklook/coordinator/`): 単一オーケストレーター、RPC でタイル生成ジョブを発行
- **Generator** (`src/quicklook/generator/`): 複数ワーカー (k8s Pod) でタイルを処理
- **Database**: タイル状態の永続化
- **Frontend** (`src/quicklook/frontend/`): REST + WebSocket API

**タイル生成パイプライン** (`quicklook` = `(exposure, dataType)` 単位):
1. **GenerateSingleFitsTiles**: FITS → タイル変換
2. **MergeSingleFitsTiles**: Generator 間でタイルマージ
3. **TransferPackedTiles**: 4×4 タイルをパック → S3 アップロード

---

## ディレクトリ構造

| パス | 目的 |
|------|------|
| `src/quicklook/coordinator/` | RPC ハブ、ジョブ管理、ハートビート |
| `src/quicklook/generator/` | タイル生成・マージ・転送ワーカー |
| `src/quicklook/frontend/` | UI 向け REST + WebSocket API |
| `src/quicklook/datasource/` | データ層抽象化 (Butler/dummy) |
| `src/quicklook/utils/rpc/` | HTTP ストリーミング RPC レイヤー |
| `src/quicklook/object_storage/` | S3/MinIO 操作 |
| `src/quicklook/job/` | ジョブ管理 |
| `tests/` | 単体テスト |
| `tests/integration_tests/` | フルシステムテスト |

### 主要ファイル

| ファイル | 内容 |
|---------|------|
| `src/quicklook/types.py` | コア型定義 (Visit, TilePos, CcdId 等) |
| `src/quicklook/config.py` | Pydantic 設定 (env: `QUICKLOOK_*`) |
| `pytest.ini` | テスト設定 |

---

## Python 開発

### 環境

- Python 3.13 を `./.venv` に使用
- 常に `./.venv/bin/{python,pip,pytest}` を明示的に使用

### コードスタイル

- 近代的な型ヒント: `list[int]` (not `List[int]`)、`int | None` (not `Optional[int]`)
- 自明なコメントは避け、高レベルの説明を書く
- コメントは **なぜ** を説明する、**何を** ではなく

### 依存ライブラリ

- SQLAlchemy 2.0+ (新しい `select()` API)
- FastAPI + uvicorn
- pydantic-settings (設定管理)
- カスタム: `mineo-fits-decompress` (`lib/` ローカルパッケージ)

---

## テスト

### Pytest 設定 (`pytest.ini`)

- 高速テストはデフォルトで実行
- 遅いテストに `@pytest.mark.slow` を付ける（デフォルトでは除外）
- 非同期テストは自動検出（`@pytest.mark.asyncio` は不要）
- データソースはデフォルトで `dummy`（Butler 依存性なし）
- S3 モックエンドポイントはテスト用に自動設定

### テスト構造

- 関数ベースのテスト（`class Test*` は使わない）
- 共置: `src/quicklook/job/__init__.py` → `src/quicklook/job/test_job.py`
- 統合テスト用フィクスチャ: `tests/integration_tests/conftest.py`

### コマンド

```bash
make test              # 高速テストのみ
make test/all          # 遅いテストも含む
make test/cov-server   # カバレッジを localhost:4000 で表示
```

---

## 型チェック

```bash
make pyright           # ワンショット
make pyright/watch     # ウォッチモード
```

---

## 設定 (`src/quicklook/config/`)

- `Config` クラスは `pydantic-settings` を使用
- 環境変数プレフィックス: `QUICKLOOK_*`
- ネスト区切り: `__` (例: `QUICKLOOK_s3_tile__access_key`)
- テスト環境: `pytest.ini` が `QUICKLOOK_environment=test` を設定

---

## RPC 通信 (`src/quicklook/comm/`)

- Coordinator → Generator は HTTP ストリーミング上で pickle 化した関数呼び出し
- Generator は定期的なハートビートで Coordinator に登録
- Coordinator は Generator の可用性とキャパシティを追跡
- 例: `Rpc.create(generate_single_fits_tiles, job, ccd_refs)`

---

## データソース (`src/quicklook/datasource/`)

- 抽象: `DataSourceBase` に `query_visits()`, `list_ccds()`, `get_data()`, `get_metadata()` を定義
- 実装: `butler`（本番）、`dummy`（テスト）
- インスタンス取得: `from quicklook.datasource import get_datasource`

---

## オブジェクトストレージ (`src/quicklook/object_storage/`)

- PackedTiles (4×4 グループ) は S3 に `pickle` リストとして保存
- キー: `quicklooks/{visit}/packed-tile/{level}/{i}/{j}.npy.zstd.list.pickle`
- LRU キャッシュあり、タイルは ~100-200KB、パック済みは ~1.6-3.2MB

---

## エラーハンドリングと信頼性

### Coordinator

- Generator が安定していると仮定しない。定期的にヘルスチェックしプルーニング
- PostgreSQL に復旧可能なジョブ状態を保存（再起動後の復旧用）

### Generator

- 予期せず逐出可能 (k8s OOM) → メモリに状態を永続化しない
- タスク失敗をグレースフルに処理、ストリーミングレスポンス経由で報告

### HTTP 呼び出し

- 明示的タイムアウト (`config.generate_timeout`, `merge_timeout`, `transfer_timeout`)

---

## ロギングとデバッグ

### ロガー階層

- `uvicorn` — HTTP リクエスト/レスポンスログ (FastAPI)
- `uvicorn.{module_name}` — アプリ固有ログ

### Timeit 測定

- `config.timeit_log_level` でログ出力（デフォルト: debug）
- 操作時間を追跡してパフォーマンス監視

### Pod ステータスエンドポイント

- `GET /api/status` — すべての Pod の CPU/メモリ/ディスク（リアルタイム）

---

## ドメイン固有の概念

### Visit と CCD 参照

- `VisitName`: フォーマット `<parts>:<data_type>:<name>`（例: `exp123:raw:visit001`）
- `CcdDataRef`: `(visit, ccd)` の組で FITS データを一意に識別
- `TilePos`: `(level, i, j)`。レベル 0 が最も細かい

### ジョブ管理 (`src/quicklook/job/`)

- `Job`: パイプライン内の作業単位
- ローカルストレージ: 中間タイル用に `config.job_local_dir`
- Generator キャパシティ: `config.generator_max_concurrent_jobs`

---

## よくある落とし穴

- RPC 関数は Coordinator と Generator の両方から import 可能でなければならない
- Generator は再起動する可能性あり（k8s OOM）→ 状態は DB に保存
- テストでは `config.data_source=dummy` で Butler 依存を回避

---

## 国際化

- `*.ja.md` は日本語ドキュメント
- 翻訳が求められた場合、対応する英語版 `*.md` を生成
