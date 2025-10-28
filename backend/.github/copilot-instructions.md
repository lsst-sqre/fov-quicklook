# FOV-Quicklook バックエンド向け Copilot 指示

## アーキテクチャ概要

`/docs/concept.ja.md` を読んでシステム設計と用語を確認してください。

**目的**: LSST カメラ画像（1ショットあたり189個の FITS ファイル、合計約12GB）をタイル方式で迅速に可視化すること。

**主要コンポーネント**（TCP 通信するプロセス）:
- **Coordinator** (`src/quicklook/coordinator/`)：単一のオーケストレーターで、RPC を通じてタイル生成ジョブを発行します
- **Generator** (`src/quicklook/generator/`)：複数のワーカー（k8s の Pod、性能は変動）でタイルを処理します
- **Database**：タイルの状態（進行中、完了）を永続化します
- **Frontend**：ユーザーがタイルを取得・合成するためのインターフェース

**タイル生成パイプライン**（`quicklook` = `(exposure, dataType)` 単位）:
1. **GenerateSingleFitsTiles**: 動的な FITS→タイル 変換（プレビューを可能にします）
2. **MergeSingleFitsTiles**: ジェネレータ間のタイルマージ
3. **TransferPackedTiles**: 4×4 タイルをパック → S3 にアップロード

- **RPC 通信** (`src/quicklook/comm/`): Coordinator→Generator は HTTP ストリーミング上で pickle 化した関数呼び出しで行われます
  - ジェネレータは定期的なハートビートで Coordinator に登録します
  - Coordinator はジェネレータの可用性とキャパシティを追跡します
  - 例: `Rpc.create(generate_single_fits_tiles, job, ccd_refs)`
- **パイプラインステージ** (`src/quicklook/utils/pipeline/`): 設定可能な並列度での同時マルチステージ処理（`config.pipeline_*` を参照）

## Python 開発

**環境**:
- Python 3.13 を `./.venv` に使用します
- いつも `./.venv/bin/{python,pip,pytest}` を明示的に使ってください

**コードスタイル**:
- 近代的な型ヒントを使ってください: `List[int]` ではなく `list[int]`、`Optional[int]` ではなく `int | None` を用いてください
- 自明なコメントは避け、高レベルの説明を書くこと
- 例: `src/quicklook/types.py` の `VisitName` は `.data_type` と `.name` プロパティを持つ文字列サブクラスです

**テスト** (`pytest.ini` 設定済み):
- `def test_*` の関数を使ってください（`class Test*` は使わない）
- 共置: `src/quicklook/job/__init__.py` に対するテストは `src/quicklook/job/test_job.py` に置く
- 非同期テストは自動検出されます（上書きしない限り `@pytest.mark.asyncio` は不要）
- 重いテストには `@pytest.mark.slow` を付ける（デフォルトでは除外されます）
- デッドロックリスクにはタイムアウトを付ける

**依存ライブラリ**:
- SQLAlchemy 2.0+（新しい `select()` API を使う）
- FastAPI + uvicorn（coordinator/generator アプリ）
- カスタムライブラリ: `mineo-fits-decompress`（`lib/` にあるローカルパッケージ）

## 主要ワークフロー

**テスト実行**:

```bash
make test              # Fast tests only
make test/all         # Include slow tests
make test/cov-server  # View coverage at localhost:4000
```

**型チェック**:

```bash
make pyright        # One-shot type check
make pyright/watch  # Watch mode
```

**設定** (`src/quicklook/config/`):
- `Config` クラスは `pydantic-settings` を使います
- 環境変数プレフィックス: `QUICKLOOK_*`、ネスト区切りは `__`
- テスト環境: `pytest.ini` が `QUICKLOOK_environment=test` と S3 設定をセットします

**データソース** (`src/quicklook/datasource/`):
- 抽象: `DataSourceBase` に `query_visits()`, `list_ccds()`, `get_data()`, `get_metadata()` が定義されています
- 実装: `butler`（本番用）、`dummy`（テスト用）
- インスタンス取得: `from quicklook.datasource import get_datasource`

## ドメイン固有の概念

**Visit と CCD 参照**:
- `VisitName`: フォーマット `<parts>:<data_type>:<name>`（例: `exp123:raw:visit001`）
- `CcdDataRef`: `(visit, ccd)` の組で FITS データを一意に識別
- `TilePos`: `(level, i, j)`。レベル 0 が最も細かく、レベルが増えるごとにタイルサイズが倍になります

**オブジェクトストレージ** (`src/quicklook/object_storage/`):
- PackedTiles（4×4 グループ）は S3 に `pickle` リストとして保存されます
- キー: `quicklooks/{visit}/packed-tile/{level}/{i}/{j}.npy.zstd.list.pickle`
- `get_packed_tile_array()` に LRU キャッシュがあり、タイルは ~100-200KB、パック済みは ~1.6-3.2MB です

**ジョブ管理** (`src/quicklook/job/`):
- `Job`: パイプライン内の作業単位
- ローカルストレージ: 中間タイル用に `config.job_local_dir`
- ジェネレータのキャパシティ: `config.generator_max_concurrent_jobs`

## 国際化

- `*.ja.md` は日本語ドキュメントです
- 翻訳が求められた場合、対応する英語版 `*.md` を生成します（存在する場合は上書きします）

## よくある落とし穴

- RPC 関数は coordinator と generator の両方から import 可能でなければなりません
- ジェネレータは再起動することがある（k8s OOM）→ 状態はデータベースに保存し、ジェネレータのメモリに頼らないでください
- テストでは `config.data_source=dummy` を使って Butler 依存を避けてください

## 追加メモ

- 変更箇所に Add などのコメントは不要です。
- Python のコードでは可能な限り型ヒントを使ってください。
- Python のバージョンは 3.13 以上を仮定してください。型ヒントでは `List[int]` より `list[int]`、`Optional[int]` より `int | None` を使用してください。
