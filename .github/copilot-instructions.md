# FOV-Quicklook AIエージェント向けシステムガイド

## システムの概要

**FOV-Quicklook** は LSST カメラ画像の分散タイル型可視化システムです。1回の観測あたり189個の FITS ファイル（合計約12GB）を数秒以内に任意のズームレベルでレンダリングします。

**アーキテクチャ図**:
```
[ユーザーブラウザ] 
    ↓
[フロントエンド (React, 複数 Pod)]
    ↓
[コーディネーター (単一 Pod) — オーケストレーター & RPC ハブ]
    ↓
[ジェネレーター (複数 Pod, 本番環境では約9個)]
    ├→ データソース (Butler) から FITS を取得
    ├→ タイルを生成 (ローカル一時ストレージ)
    └→ オブジェクトストレージ (S3) にマージしてアップロード
    
[PostgreSQL データベース] — ジョブ復旧用の永続状態
[MinIO / S3 ストレージ] — パック済みタイルキャッシュ (4×4 グループあたり ~1.6-3.2MB)
```

**3段階のタイル生成パイプライン**:
1. **GenerateSingleFitsTiles**: 生の FITS → タイル変換 (プレビューを可能にする)
2. **MergeSingleFitsTiles**: ジェネレーター間のタイルマージ (複数の CCD にまたがるタイル)
3. **TransferPackedTiles**: 4×4 グループを圧縮 → S3 にアップロード

概念的な背景については `/docs/concept.ja.md` と `/backend/README.ja.md` を参照してください。

---

## プロジェクト構成

```
backend/                # Python 3.13 バックエンド (FastAPI)
  src/quicklook/
    coordinator/        # RPC ハブ、ジョブオーケストレーション、ハートビート管理
    generator/          # タイル生成、マージ、転送 (並列ワークロード)
    frontend/           # UI 用 Web API (REST + WebSocket)
    datasource/         # データ層の抽象化 (Butler またはテスト用 dummy)
    db/                 # SQLAlchemy モデル (PostgreSQL)
    utils/
      rpc/              # HTTP ストリーミング RPC レイヤー
      comm/             # IPC ユーティリティ
      pipeline/         # 設定可能なマルチステージパイプライン
    types.py            # コア定義型 (Visit, TilePos, CcdId など)
    config.py           # Pydantic 設定 (env: QUICKLOOK_*)
  tests/
    integration_tests/  # フルシステムテスト (コーディネーター + ジェネレーター + フロントエンド自動起動)
    coordinator/        # コーディネーターロジックのユニットテスト
    generator/          # ジェネレーターロジックのユニットテスト
    ...
  pytest.ini            # 設定: "slow" を自動マーク、デフォルトで dummy データソース使用
  .github/copilot-instructions.md  # 詳細なバックエンド慣例

frontend/app/           # React + TypeScript + Vite
  src/
    pages/              # Quicklook ビューアー、管理パネル (Pod 状態、キャッシュ管理)
    store/api/          # RTK Query フック (OpenAPI スキーマから自動生成)
    StellarGlobe/       # 3D 球面ビューアーコンポーネント
  .github/copilot-instructions.md  # SCSS ビルドノート

k8s/                    # Kubernetes Helm チャート (Phalanx 統合)
  phalanx/
    applications/fov-quicklook/  # デプロイ用 Helm チャート
    
docs/
  concept.ja.md         # システム設計と用語 (日本語)
  dev.ja.md             # 開発環境設定 (日本語)
  request.md            # HTTP API リクエスト例
  tasks.ja.md           # タスク定義 (日本語)

notes/
  requirements.md       # Pod レプリカ数、リソースリミット、キャッシュ設定
  templating.md         # Helm テンプレート注記
```

---

## クリティカルな統合ポイント

### フロントエンド ↔ コーディネーター (REST API)

**ベース URL**: `QUICKLOOK_coordinator_base_url` で設定 (デフォルト: `http://localhost:9501`)

**主要なエンドポイント**:
- `POST /api/quicklooks` — 観測のタイル生成をリクエスト
- `GET /api/quicklooks/{id}` — ジョブ状態とメタデータを確認
- `GET /api/tiles/{z}/{x}/{y}` — タイル取得 (S3 キャッシュから)
- `GET /pod_status` — システムヘルス (ジェネレーター統計を集約)
- `GET /healthz` — ライブネスチェック (登録済みジェネレーターリストを返す)

**実装**: `backend/src/quicklook/coordinator/api/` (FastAPI ルーター)

**フロントエンドからのアクセス**: `frontend/app/src/store/api/openapi.ts` (OpenAPI スキーマから自動生成された RTK Query フック)

### コーディネーター ↔ ジェネレーター (HTTP 上の RPC)

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

### データフロー: データソース → ジェネレーター → オブジェクトストレージ

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

---

## 開発者ワークフロー

### バックエンド開発のセットアップ

**初期セットアップ**:
```bash
cd backend
python3.13 -m venv .venv
./.venv/bin/pip install -e .
```

**ローカルで3つのコンポーネントを実行** (別々のターミナル):
```bash
# ターミナル 1: コーディネーター (ポート 9501)
make dev/coordinator

# ターミナル 2: ジェネレーター (ポート 9502)
make dev/generator

# ターミナル 3: フロントエンド (ポート 9500)
make dev/frontend
```

**テスト実行**:
```bash
make test              # 高速テストのみ (デフォルト: @pytest.mark.slow をスキップ)
make test/all          # 遅いテストも含む
make test/cov-server   # localhost:4000 でカバレッジ HTML を表示
```

**型チェック**:
```bash
make pyright           # 一度の実行
make pyright/watch     # 継続的監視
```

**統合テスト** (フルシステム、自動起動):
```bash
make test/all          # tests/integration_tests/ の統合テストはすべてのコンポーネントを自動起動
```

詳細は `backend/.github/copilot-instructions.md` を参照してください (Python パターン、テスト規約、設定、RPC 設計)。

### フロントエンド開発

**初期セットアップ**:
```bash
cd frontend/app
npm install
```

**開発サーバー**:
```bash
npm run dev  # Vite 開発サーバー、通常 http://localhost:5173
```

**SCSS スタイル編集後**:
```bash
npm run scss-types  # スタイル型定義を再生成
```

**サーバーサイドのAPIに合わせてクライアントサイドのAPI呼び出しのためのコードの更新**:
```bash
npm run api:rtk-query
```

**本番ビルド**:
```bash
npm run build       # dist/ を作成
npm run preview      # ローカルで本番ビルドをテスト
```

詳細は `frontend/app/.github/copilot-instructions.md` を参照してください。

### Kubernetes へのビルドとデプロイ

**Docker イメージをビルド**:
```bash
make build                              # 高速ビルド
PYRIGHT_BEFORE_PUSH=1 make build        # バックエンド型チェック含む
```

**ローカル k8s レジストリにプッシュ**:
```bash
make push  # localhost:32000/quicklook にプッシュ (GHCR の場合は make push-to-ghcr)
```

**k8s クラスターにデプロイ**:
```bash
make deploy       # ビルド、プッシュ、ポッド再起動
make dev-update   # デバッグ値でヘルムアップグレード (notes/dev-values.yaml を参照)
```

**ポッドを再起動** (リビルドなし):
```bash
make restart  # 既存のコーディネーター、ジェネレーター、フロントエンドポッドを削除
```

---

## 一般的な開発タスク

| タスク | 方法 | 場所 |
|--------|------|------|
| REST エンドポイント追加 | `coordinator/api/`、`generator/api/`、`frontend/api/` のルーターを編集 | `backend/src/quicklook/{coordinator,generator,frontend}/api/*.py` |
| RPC タスク追加 | `tasks.py` に `Task` データクラスを定義、ジェネレーターでハンドラーを実装 | `backend/src/quicklook/coordinator/quicklookjob/tasks.py` + `backend/src/quicklook/generator/api/tile*.py` |
| フロントエンドページ追加 | `pages/` に `.tsx` を作成、ルーターを更新 | `frontend/app/src/pages/` |
| 設定を追加 | `Config` クラスにフィールドを追加、環境変数プレフィックスをドキュメント化 | `backend/src/quicklook/config.py` |
| 特定のテスト実行 | `make test -- -k test_name` または `make test -- -k TestClass` | `backend/pytest.ini` は高速デフォルトに設定済み |
| テスト失敗をデバッグ | `-vv` で実行: `make test -- -vv -k test_name` | 非同期テストは `asyncio_mode=auto` で自動検出 |
| k8s ポッドログを確認 | `kubectl -n quicklook logs pod/<pod-name> --tail=100` | すべてのポッドは `quicklook` 名前空間下 |
| タイルキャッシュを監視 | 管理ページ: http://localhost:9500/admin (`config.admin_page=true` の場合) | `backend/src/quicklook/coordinator/api/admin_page.py` |
| キャッシュをクリア | 同じ管理ページまたは `POST /kill` (開発環境のみ) | k8s: ポッド削除 → キャッシュ消去、次のリクエストで再生成 |
| システムヘルスを確認 | curl `http://localhost:9500/api/status` (フロントエンドが集約) | コーディネーター + すべてのジェネレーター + フロントエンドの CPU/メモリ/ディスク を返す |

---

## プロジェクト全体の慣例

### コードスタイルと型ヒント

**Python** (詳細は `backend/.github/copilot-instructions.md` を参照):
- 型ヒントが必須: `list[int]` (not `List[int]`)、`int | None` (not `Optional[int]`)
- コード内に「Add」などの明白なコメントを付けない。高レベルの説明を書く
- コメントは **なぜ** を説明する、 **何を** ではなく。例: "適応的ディスパッチは Pod の不均一な性能に対応するため停滞したタスクを再キューイングする"

**TypeScript/React**:
- 厳密な型チェックを使用 (`any` は `// @ts-ignore` + コメント必須)
- 関数型コンポーネント推奨、状態/エフェクトにはフック

### 命名規約

**コア定義型**:
- **Visit**: 文字列サブクラス (形式: `<parts>:<data_type>:<name>`、例: `raw:broccoli`)、`.data_type` と `.name` プロパティを持つ
- **TilePos**: `(level, i, j)` — レベル 0 が最も細かく、レベルが高いほど粗い (ズームアウト)
- **CcdId** / **CcdDataRef**: FITS 露出を一意に識別する Visit + CCD 名ペア
- **GeneratorPod**: `(host, port)` — k8s Pod の識別
- **Quicklook**: `(Visit, data_type)` — タイル生成作業の単位

**環境変数**: `QUICKLOOK_*` プレフィックスで、ネストは `__` で区切る (例: `QUICKLOOK_s3_tile__access_key`)

### テスト パターン

**Pytest 設定** (`backend/pytest.ini`):
- 高速テストはデフォルトで実行。遅いテストに `@pytest.mark.slow` を付ける
- 非同期テストは自動検出 (手動で `@pytest.mark.asyncio` は不要)
- データソースはデフォルトで `dummy` (Butler 依存性なし)
- S3 モックエンドポイントはテスト用に自動設定

**テスト構造**:
- 関数ベースのテスト (テストクラスなし)
- 共置: `src/quicklook/x/y.py` → `src/quicklook/x/test_y.py`
- コーディネーター/ジェネレーター生成用フィクスチャ: `backend/tests/integration_tests/conftest.py`

### エラーハンドリングと信頼性

**コーディネーター**:
- ジェネレーターが安定していると仮定しない。定期的にヘルスチェックしプルーニングする
- PostgreSQL に復旧可能なジョブ状態を保存。再起動して復旧できる

**ジェネレーター**:
- 予期せず逐出可能 (k8s OOM) → メモリに状態を永続化しない
- タスク失敗をグレースフルに処理し、ストリーミングレスポンス経由で報告

**すべての HTTP 呼び出し**:
- 明示的タイムアウト (`config.generate_timeout`、`merge_timeout`、`transfer_timeout`)

### ロギングとデバッグ

**ロガー階層**:
- `uvicorn` — HTTP リクエスト/レスポンスログ (FastAPI)
- `uvicorn.{module_name}` — アプリ固有ログ

**Timeit 測定**:
- `config.timeit_log_level` でログ出力 (デフォルト: debug)
- 操作時間を追跡してパフォーマンス監視

**Pod ステータスエンドポイント**:
- `GET /api/status` — すべてのポッドの CPU/メモリ/ディスク (リアルタイム)
- パフォーマンスボトルネックを診断するのに役立つ

---

## 重要なファイルと決定ポイント

| 決定 | 参照先 |
|------|-------|
| "新しい設定を追加するには?" | `backend/src/quicklook/config.py` に Pydantic フィールドを追加。環境変数は自動的に `QUICKLOOK_<field_name>` になる |
| "永続状態をどこに保存?" | PostgreSQL データベース (SQLAlchemy モデル: `backend/src/quicklook/db/`) — ジェネレーターメモリには永続化しない |
| "コーディネーターからジェネレーターを呼び出すには?" | `Rpc.create()` + RPC ハンドラーを使用 (参照: `backend/src/quicklook/rpc/` と `backend/README.ja.md` の例) |
| "Butler なしでテストするには?" | `config.data_source=dummy` を使用。`pytest.ini` が自動的に設定 |
| "ジェネレーター再起動を処理するには?" | すべての状態が失われていると仮定。再ディスパッチが必要なインフライトジョブをデータベースで確認 |

---

## よくある落とし穴と解決方法

| 落とし穴 | 原因 | 解決方法 |
|--------|------|--------|
| "RPC 呼び出しがインポートエラーで失敗" | ハンドラー関数が両方のモジュールからインポート不可 | ハンドラーを共有モジュール (例: `backend/src/quicklook/generator/api/tilegenerate.py`) に配置 |
| "k8s ポッド再起動後にジェネレーター状態が消失" | ジェネレーター処理メモリに作業状態を保存 | すべての永続状態を PostgreSQL に移動。起動時にジェネレーターが DB から読み込む |
| "Butler 依存性でテストが失敗" | データソース設定が間違っている | `pytest.ini` が `QUICKLOOK_data_source=dummy` に設定されていることを確認。または Butler セットアップで `make test/all` 実行 |
| "タイル転送がタイムアウト" | ネットワークまたはオブジェクトストレージの遅延 | `config.transfer_timeout` を増加。S3 エンドポイント到達可能性を確認。ネットワークポリシーを確認 |
| "コーディネーターがジェネレーターを発見できない" | ジェネレーター登録が失敗またはハートビートをスキップ | ジェネレーターログで `POST /register_generator` 失敗を確認。`config.heartbeat_interval` を確認 |

---

## ドキュメントマップ

**システム設計**:
- `/docs/concept.ja.md` — アーキテクチャ、コンポーネント役割、パイプラインフェーズ (日本語)
- `/backend/README.ja.md` — バックエンド概要とセットアップ (日本語)

**開発**:
- `/docs/dev.ja.md` — ローカル開発環境 (日本語)
- `/notes/requirements.md` — Pod レプリカ数、リソースリミット、キャッシュサイズ
- `/backend/.github/copilot-instructions.md` — 詳細な Python 慣例、テスト、RPC、設定
- `/frontend/app/.github/copilot-instructions.md` — SCSS ビルド、型生成

**API リファレンス**:
- `/docs/request.md` — HTTP リクエスト例
- `frontend/app/src/store/api/openapi.ts` — 自動生成 API クライアント (OpenAPI スキーマから)

**デプロイ**:
- `/k8s/phalanx/applications/fov-quicklook/README.md` — Helm チャートドキュメント

---

## クイックスタート チェックリスト

1. **クローンとセットアップ**: `git clone ...`, `cd backend && python3.13 -m venv .venv && ./.venv/bin/pip install -e .`
2. **ローカルで実行**: `make dev/coordinator`, `make dev/generator`, `make dev/frontend` (3ターミナル)
3. **テスト実行**: `make test` (高速) または `make test/all` (遅いテスト含む)
4. **コンポーネントドキュメント読み込み**: Python パターン については `backend/.github/copilot-instructions.md` を参照
5. **アーキテクチャ探索**: `/docs/concept.ja.md` をブラウザまたはエディタで開く
6. **デプロイ**: `make build && make push && make deploy` (Kubernetes クラスター実行中)

---

## ドキュメント保守ポリシー

**このドキュメントは生きたドキュメントであり、プロジェクトの重大な変更とともに更新する必要があります。**

### 更新が必要なケース

以下の場合、このドキュメント (`.github/copilot-instructions.md`) を更新してください:

1. **新しいコンポーネントやサービスの追加**
   - 例: 新しいマイクロサービス、新しい k8s リソース、データ層の変更
   - 更新: プロジェクト構成セクションに追加

2. **主要なアーキテクチャ変更**
   - 例: RPC 通信方式の変更、新しいタイル生成フェーズ、状態管理の再設計
   - 更新: システム概要、クリティカルな統合ポイント、アーキテクチャ図

3. **ワークフロー/コマンドの追加または変更**
   - 例: 新しい make ターゲット、テスト実行方法の変更、デプロイプロセスの更新
   - 更新: 開発者ワークフロー、一般的な開発タスク

4. **新しい規約やベストプラクティス**
   - 例: 新しい命名規則、テストパターン、エラーハンドリング戦略の確立
   - 更新: プロジェクト全体の慣例セクション

5. **既知の落とし穴や限界の発見**
   - 例: パフォーマンス問題、統合の落とし穴、デバッグのコツ
   - 更新: よくある落とし穴と解決方法、重要なファイルと決定ポイント

### 更新プロセス

1. **変更をコミットする前に**: コードの重大な変更 (PR) をする際、このドキュメントが古くなっていないか確認
2. **レビュー時に**: PR レビュアーは、このドキュメントが更新の対象かどうかをチェック
3. **更新する際の手順**:
   - 変更対象のセクションを特定
   - 構体な例とファイルパスを含めて更新
   - 関連する他のセクションも整合性を確認
   - CI/CD チェックを通す前に、ドキュメントが正確であることを確認

### 質問がある場合

このドキュメントについて質問や不明な点がある場合、または AI エージェント (GitHub Copilot など) のために追加情報が必要な場合は、次の場所を参照してください:

- **バックエンド詳細**: `backend/.github/copilot-instructions.md`
- **フロントエンド詳細**: `frontend/app/.github/copilot-instructions.md`
- **概念的背景**: `/docs/concept.ja.md`、`/backend/README.ja.md`
- **API リクエスト例**: `/docs/request.md`

---

**質問?** コンポーネント固有の copilot 指示を確認するか、コードベースから例を grep してください (例: `grep -r "GenerateTask" backend/src/` で全 RPC タスク使用を検索)。
