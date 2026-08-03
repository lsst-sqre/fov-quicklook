# FOV-Quicklook AIエージェント向けシステムガイド

## ドキュメントツリー

このファイルはプロジェクト全体の概要を提供します。詳細は以下を参照してください：

| 対象 | ドキュメント |
|------|-------------|
| **システム構成** | `/dev-docs/architecture.ja.md` |
| **開発環境 (microk8s)** | `/dev-docs/dev.ja.md` |
| **バックエンド開発** (Python) | `/dev-docs/backend.ja.md` |
| **フロントエンド開発** (React/TypeScript) | `/dev-docs/frontend.ja.md` |
| **CI / review app** | `/dev-docs/ci.ja.md` |
| **デプロイ (Phalanx)** | `/dev-docs/phalanx.ja.md` |

---

## システム概要

**目的**: LSST カメラ画像（1ショット = 189 FITS ファイル、約12GB）を数秒以内にタイル形式で可視化

### コンポーネント構成

| コンポーネント | 役割 | スケール |
|---------------|------|----------|
| **Frontend** | UI提供 (React + Vite) | 複数Pod |
| **Coordinator** | RPCハブ、ジョブ管理、動的ディスパッチ | 単一Pod |
| **Generator** | FITS→タイル変換、マージ、S3転送 | 約9Pod (本番) |
| **PostgreSQL** | ジョブ状態永続化（再起動復旧用） | 単一 |
| **MinIO/S3** | PackedTilesキャッシュ | - |

**データフロー**: `ブラウザ → Frontend → Coordinator → Generator(s) → S3`

### タイル生成パイプライン（3段階）

| フェーズ | 処理内容 | 完了時の状態 |
|---------|---------|-------------|
| 1. **GenerateSingleFitsTiles** | FITS → タイル変換 | プレビュー表示可能 |
| 2. **MergeSingleFitsTiles** | Generator間でタイルマージ | 複数CCD境界が結合済み |
| 3. **TransferPackedTiles** | 4×4グループを圧縮 → S3アップロード | キャッシュ完了 |

詳細: `/dev-docs/architecture.ja.md`

---

## プロジェクト構成

### ディレクトリ構造

| パス | 目的 | 詳細 |
|------|------|------|
| `backend/` | Python バックエンド (FastAPI) | `/dev-docs/backend.ja.md` |
| `frontend/app/` | React フロントエンド | `/dev-docs/frontend.ja.md` |
| `frontend/lib/stellar-globe/` | フロントエンドが参照するローカル package 群 | **Git submodule**。clone 直後は `git submodule update --init --recursive` が必要 |
| `dev/deploy-broker/` | agent-safe deploy/sync/restart broker (Python daemon/client) | `/dev-docs/phalanx.ja.md` |
| `k8s/phalanx/` | Helm チャート（独立gitリポジトリ） | `/dev-docs/phalanx.ja.md` |
| `dev-docs/` | 開発者向けドキュメント | **日本語で維持する** |
| `docs/` | 補助的なメモ・ルーティング資料 | - |

> **注意**: `k8s/phalanx/` はプロジェクトルートとは別の独立した git リポジトリ（`https://github.com/lsst-sqre/phalanx.git`）です。
> `.gitignore` で除外されており、サブモジュールではありません。ローカルにクローンして使用します。

---

## プロジェクト全体の慣例

### コメントスタイル

- コード内に「Add」などの自明なコメントを付けない
- コメントは **なぜ** を説明する、 **何を** ではなく

### 命名規約（コア型）

| 型 | 説明 |
|----|------|
| **VisitName** | 文字列サブクラス。`.data_type` と `.name` プロパティを持つ |
| **TilePos** | `(level, i, j)` — レベル 0 が最も細かい |
| **CcdDataRef** | `(visit, ccd)` — FITS 露出を一意に識別 |

### 環境変数

- プレフィックス: `QUICKLOOK_*`
- ネスト区切り: `__` (例: `QUICKLOOK_s3_tile__access_key`)

### ドキュメント言語

- `dev-docs/` 配下のドキュメントは日本語で書く

### デプロイ / 検証の標準認証情報

- usdf-dev の `deploy-broker` を使うときは、まず `~/.fov-quicklook2/broker-url` と `~/.fov-quicklook2/broker-token` を確認する
- `dev/deploy-broker/` の client には `--server "$(cat ~/.fov-quicklook2/broker-url)"` と `--api-token "$(cat ~/.fov-quicklook2/broker-token)"` を渡す
- app 側の live 確認は、broker の `get-app-token` から得た token を優先し、`dev/.gafaelfawr-token` は fallback として扱う

---

## ドキュメントマップ

### システム設計
- `/dev-docs/architecture.ja.md` — システム構成、データフロー、運用前提
- `/dev-docs/features/butler-data-query.ja.md` — Data Query と Butler registry/dataset の関係

### 開発
- `/dev-docs/dev.ja.md` — microk8s 前提の開発ワークフロー
- `/dev-docs/backend.ja.md` — バックエンド固有の規約・テスト・設定
- `/dev-docs/frontend.ja.md` — フロントエンド固有の規約・ビルド・テスト

### CI / review app
- `/dev-docs/ci.ja.md` — review app の CI フローと shared fixture

### 補助資料
- `/docs/routes.md` — 画面ルーティングのメモ
- `/docs/templating.md` — テンプレート関連のメモ

### デプロイ
- `/dev-docs/phalanx.ja.md` — Phalanx デプロイメント ガイド
- `dev/deploy-broker/` — agent-safe deploy / sync / restart broker 実装
- `/k8s/phalanx/applications/fov-quicklook/README.md` — Helm チャート

---

## 一時ファイルの書き出し

- `/tmp` を使用しないこと（エージェントは自動では `/tmp` にアクセスできない）
- 一時的な結果ファイルはプロジェクト内の `.gitignore` で除外されたディレクトリ（例: `/copilot/`）に書き込むこと

---

## ターミナル操作時の注意

- コマンドが `^C` で中断された場合、**指示者が意図的に中断した可能性がある**
- `^C` 中断を検出したら、自動でリトライせず `./copilot/ask_for_instructions` で指示者に確認を取ること

---

## ドキュメント保守ポリシー

以下の場合、適切なドキュメントを更新してください：

- **プロジェクト全体に関わる変更**: このファイル (`.github/copilot-instructions.md`)
- **開発フローの変更**: `dev-docs/dev.ja.md`
- **バックエンド固有の変更**: `dev-docs/backend.ja.md`
- **フロントエンド固有の変更**: `dev-docs/frontend.ja.md`
- **CI / review app の変更**: `dev-docs/ci.ja.md`
- **デプロイ手順の変更**: `dev-docs/phalanx.ja.md`
