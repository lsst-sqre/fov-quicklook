# 開発ノート

## クイックスタート チェックリスト

1. **クローンとセットアップ**: `git clone ...`, `make setup/agent-worktree`, `cd backend && python3.13 -m venv .venv && ./.venv/bin/pip install -e .`
2. **ローカルで実行**: `make dev/coordinator`, `make dev/generator`, `make dev/frontend` (3ターミナル)
3. **テスト実行**: `make test` (高速) または `make test/all` (遅いテスト含む)
4. **コンポーネントドキュメント読み込み**: Python パターン については `backend/.github/copilot-instructions.md` を参照
5. **アーキテクチャ探索**: `/docs/concept.ja.md` をブラウザまたはエディタで開く
6. **デプロイ**: `make build && make push && make deploy` (Kubernetes クラスター実行中)

## 準備

* K8sクラスター
* MinIOなどのオブジェクトストレージ
* サンプルデータ

## clone / worktree 作成後の外部リポジトリ初期化

このリポジトリは clone 後に次の外部依存を materialize する必要がある。

- `frontend/lib/stellar-globe` — `https://adc-gitlab.mtk.nao.ac.jp/gitlab/michitaro/stellar-globe` 由来の vendored snapshot
- `k8s/phalanx` — `.gitignore` 対象の独立した Git repo。取得先は `https://github.com/lsst-sqre/phalanx.git`

まず一度だけ次を実行する:

```bash
make setup/agent-worktree
```

このセットアップは現在の worktree 向けに次を行う。

1. vendored `frontend/lib/stellar-globe` が存在することを確認
2. `k8s/phalanx` の clone（既存なら `fetch --prune origin`）
3. `.githooks/post-checkout` / `.githooks/post-merge` をこの worktree に登録

Git に clone hook は無いので、clone の瞬間に自動化することはできない。代わりに `make setup/agent-worktree` を clone / worktree 作成直後に必ず実行する。

`stellar-globe` を submodule にすると GitHub Actions の build 中に ADC GitLab へ接続できず deploy が失敗するため、この repo では snapshot を vendoring して管理する。

## MinIO

* `fov-quicklook-datasource`バケットを作成

---

## バックエンド開発のセットアップ

**初期セットアップ**:
```bash
make setup/agent-worktree
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

---

## フロントエンド開発

**初期セットアップ**:
```bash
make setup/agent-worktree
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

---

## Kubernetes へのビルドとデプロイ

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
