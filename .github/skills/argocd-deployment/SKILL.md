---
name: argocd-deployment
description: >
  ArgoCD経由でfov-quicklookアプリケーションのDeploymentを再起動・状態確認・ブランチ切替する。
  デプロイ、再起動、ロールアウト、ArgoCD操作、Phalanxブランチ切替に関するタスクで使用する。
  対象はusdf-rsp-devのfov-quicklookアプリケーションのみ。
---

# ArgoCD Deployment 操作スキル

## 概要

`backend/dev/argocd.sh` を使って、ArgoCD上のfov-quicklookアプリケーションのDeploymentを操作する。

## 前提条件

- ArgoCD トークンが `backend/dev/.argocd-token` に保存されていること
- トークンの有効期限は約8時間。期限切れの場合はブラウザで https://usdf-rsp-dev.slac.stanford.edu/argo-cd にログインし直してトークンを再取得する

## トークンの取得と設定

1. ブラウザで https://usdf-rsp-dev.slac.stanford.edu/argo-cd/applications/fov-quicklook にアクセス
2. 開発者ツールを開く
3. 任意のAPIリクエストを選択し「Copy as cURL」を実行
4. 以下のコマンドでトークンを抽出・保存:

```bash
cd backend/dev
./argocd.sh extract-token "<コピーしたcurlコマンド>"
```

## Deploymentの再起動

```bash
cd backend/dev

# 主要コンポーネント(coordinator, generator, frontend, debug)を再起動
./argocd.sh restart

# 特定のDeploymentだけ再起動
./argocd.sh restart coordinator
./argocd.sh restart generator frontend
```

## 状態確認

```bash
cd backend/dev
./argocd.sh status
```

出力例:
```
=== fov-quicklook Deployment 状態 ===
  fov-quicklook-coordinator: 1/1 ready  image=ghcr.io/lsst-sqre/fov-quicklook:main
  fov-quicklook-generator: 8/8 ready  image=ghcr.io/lsst-sqre/fov-quicklook:main
  fov-quicklook-frontend: 2/2 ready  image=ghcr.io/lsst-sqre/fov-quicklook:main
  fov-quicklook-db: 1/1 ready  image=postgres:16
  fov-quicklook-debug: 1/1 ready  image=jupyter/base-notebook:latest
```

## Deployment一覧

| 短縮名 | フル名 | 役割 |
|---|---|---|
| `coordinator` | `fov-quicklook-coordinator` | RPCハブ、ジョブ管理 |
| `generator` | `fov-quicklook-generator` | FITS→タイル変換 |
| `frontend` | `fov-quicklook-frontend` | UI提供 |
| `db` | `fov-quicklook-db` | PostgreSQL（通常再起動しない） |
| `debug` | `fov-quicklook-debug` | デバッグ用 |

## Podログの確認

```bash
cd backend/dev

# coordinatorのログを表示（デフォルト）
./argocd.sh logs

# 特定コンポーネントのログ
./argocd.sh logs generator
./argocd.sh logs frontend
```

Podが起動に失敗している場合、ログの末尾にエラーメッセージが表示される。

## Phalanxリポジトリの参照ブランチ管理

ArgoCDのfov-quicklookアプリケーションは `lsst-sqre/phalanx` リポジトリの特定ブランチを参照している。

> **注意**: `k8s/phalanx/` はプロジェクトルートとは別の独立した git リポジトリ（`https://github.com/lsst-sqre/phalanx.git`）です。
> `.gitignore` で除外されており、サブモジュールではありません。

ローカルの `k8s/phalanx` のブランチとArgoCDの参照ブランチが一致していない場合、設定のミスマッチが発生する。

```bash
cd backend/dev

# 現在の参照ブランチを確認
./argocd.sh get-branch

# ブランチを変更
./argocd.sh set-branch fov-quicklook/add-main-repository

# ブランチを変更して即座にsync
./argocd.sh set-branch fov-quicklook/add-main-repository --sync

# ローカルのサブモジュールのブランチを確認して合わせる場合
git -C k8s/phalanx branch --show-current
./argocd.sh set-branch (git -C k8s/phalanx branch --show-current) --sync
```

## ArgoCD sync

マニフェストをクラスタに適用する。ブランチ変更後やHelm valuesの更新後に使用。

```bash
cd backend/dev
./argocd.sh sync
```

## 技術的な仕組み

- **再起動**: ArgoCD CLI (`argocd app actions run`) を使用。`--auth-token` にブラウザのcookie JWTを渡す
- **状態確認**: ArgoCD REST API (`GET /api/v1/applications/fov-quicklook/resource`) を使用。Cookie認証
- CLIの `argocd app get` はproject get権限の問題でこの環境では使用不可

## 安全性

- 操作対象は `fov-quicklook` アプリケーションのみに制限
- ArgoCD CLIのサーバ指定: `--server usdf-rsp-dev.slac.stanford.edu --grpc-web --grpc-web-root-path /argo-cd`
- REST APIのベースURL: `https://usdf-rsp-dev.slac.stanford.edu/argo-cd/api/v1/applications/fov-quicklook/`

## ブランチ名の制約

**重要**: ブランチ名に `/` を含めるとGitHub Actionsのビルドがトリガーされない。
Dockerイメージタグにブランチ名が使われるため、`/` はハイフン `-` に置き換えること。

- ✗ `feature/alpha-channel` — ビルドがトリガーされない
- ✓ `feature-alpha-channel` — 正常にビルドされる

既存ブランチをリネームする場合:
```bash
git branch -m old-name new-name
git push origin -u new-name
git push origin --delete old-name
```

## デプロイの典型的なフロー

1. コードを変更してGitHubにpush（ブランチ名に `/` を含めないこと）
2. GitHub Actionsのビルド完了を待つ: `gh run watch --repo lsst-sqre/fov-quicklook`
3. 参照ブランチが正しいか確認: `./argocd.sh get-branch`
4. 必要ならブランチを切替: `./argocd.sh set-branch <branch>`
5. Deploymentを再起動: `./argocd.sh restart`
6. 状態を確認: `./argocd.sh status`
7. アプリケーションの動作確認: https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/
