# FOV-Quicklook AIエージェント向けシステムガイド

## 重要

`copilot/AGENT_INSTRUCTIONS.md` が存在する場合、その内容を**最優先**で厳守してください。

---

## ドキュメントツリー

このファイルはプロジェクト全体の概要を提供します。詳細は以下を参照してください：

| 対象 | ドキュメント |
|------|-------------|
| **バックエンド開発** (Python) | `backend/.github/DEVELOPMENT.md` |
| **フロントエンド開発** (React/TypeScript) | `frontend/app/.github/DEVELOPMENT.md` |
| **システム設計・概念** | `/docs/concept.ja.md` |
| **開発環境セットアップ** | `/docs/dev.ja.md` |
| **デプロイ (Phalanx)** | `/docs/phalanx.ja.md` |
| **トラブルシューティング** | `/docs/troubleshooting.ja.md` |

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

詳細: `/docs/concept.ja.md`

---

## プロジェクト構成

### ディレクトリ構造

| パス | 目的 | 詳細 |
|------|------|------|
| `backend/` | Python バックエンド (FastAPI) | `backend/.github/DEVELOPMENT.md` |
| `frontend/app/` | React フロントエンド | `frontend/app/.github/DEVELOPMENT.md` |
| `dev/deploy-broker/` | agent-safe deploy/sync/restart broker (Python daemon/client) | `/docs/phalanx.ja.md` |
| `k8s/phalanx/` | Helm チャート（独立gitリポジトリ） | `/docs/phalanx.ja.md` |
| `docs/` | 設計・開発ドキュメント | - |

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

### デプロイ / 検証の標準認証情報

- usdf-dev の `deploy-broker` を使うときは、まず `~/.fov-quicklook2/broker-url` と `~/.fov-quicklook2/broker-token` を確認する
- `dev/deploy-broker/` の client には `--server "$(cat ~/.fov-quicklook2/broker-url)"` と `--api-token "$(cat ~/.fov-quicklook2/broker-token)"` を渡す
- app 側の live 確認は、broker の `get-app-token` から得た token を優先し、`dev/.gafaelfawr-token` は fallback として扱う

---

## ドキュメントマップ

### システム設計
- `/docs/concept.ja.md` — アーキテクチャ、パイプラインフェーズ
- `/docs/architecture-decisions.ja.md` — 重要な設計決定

### 開発
- `/docs/dev.ja.md` — ローカル開発環境、ワークフロー
- `/backend/README.ja.md` — バックエンド概要とセットアップ

### 統合・トラブルシューティング
- `/docs/integration-points.ja.md` — コンポーネント間通信の詳細
- `/docs/troubleshooting.ja.md` — よくある落とし穴と解決方法

### API
- `/docs/request.md` — HTTP リクエスト例

### デプロイ
- `/docs/phalanx.ja.md` — Phalanx デプロイメント ガイド
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
- **バックエンド固有の変更**: `backend/.github/DEVELOPMENT.md`
- **フロントエンド固有の変更**: `frontend/app/.github/DEVELOPMENT.md`
