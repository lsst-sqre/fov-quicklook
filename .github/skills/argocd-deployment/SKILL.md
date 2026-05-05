---
name: argocd-deployment
description: >
  deploy broker または ArgoCD経由でfov-quicklookアプリケーションを操作する。
  デプロイ、状態確認、ログ取得、再起動、ロールアウト、ArgoCD操作、Phalanxブランチ切替に関するタスクで使用する。
  対象はusdf-rsp-devのfov-quicklookアプリケーションのみ。
---

# ArgoCD Deployment 操作スキル

## 概要

標準の agent-safe 経路では `dev/deploy-broker/` を使い、必要な場合だけ
`dev/argocd.sh` を使って ArgoCD 上の fov-quicklook アプリケーションを操作する。

> **デフォルト前提**: agent は **deploy broker daemon が動いていないノード**
> で作業する。agent は caller 側として `deploy-broker-client` を使い、必要なら
> SSH tunnel や `--server` で daemon ノードへ接続する。local endpoint に転送して
> いる場合は `http://127.0.0.1:8010` をそのまま使ってよい。

> **agent-safe 運用**: agent に GitHub / ArgoCD への直接権限を渡さない場合は、
> `dev/deploy-broker/` の broker daemon を優先する。broker は ArgoCD token を
> daemon 側に保持し、status / branch / logs / sync / restart などの制限された操作だけを
> 認証付き HTTP API で公開する。

## broker 経由の標準運用

### 前提条件

- `cd dev/deploy-broker`
- broker daemon は別ノードで起動していること
- ArgoCD token / app token を返す command が broker daemon 側で設定済みであること
- 標準運用では client から broker daemon に届くこと（通常は SSH tunnel）
- broker bearer token は `DEPLOY_BROKER_API_TOKEN_FILE` か `$HOME/.keys/FOV_QUICKLOOK_BROKER_TOKEN` で渡す

### トークンの取得と設定

1. daemon ノード側で token を返す command を用意する
2. command の stdout が `{"argocd_token":"...","gafaelfawr_token":"..."}` を返すようにする
3. `DEPLOY_BROKER_TOKEN_COMMAND` でその command を指定して daemon を起動する

```bash
cd /srv/fov-quicklook-broker-state
cat > fetch-tokens.sh <<'EOF'
#!/bin/sh
exec /path/to/real-token-command
EOF
chmod 700 fetch-tokens.sh

DEPLOY_BROKER_TOKEN_COMMAND=/srv/fov-quicklook-broker-state/fetch-tokens.sh \
  uv run --project /srv/fov-quicklook/dev/deploy-broker deploy-broker-daemon
```

daemon 起動時には、現在使われる broker bearer token も端末に表示される。`DEPLOY_BROKER_TOKEN_COMMAND` が未設定なら daemon は起動せずエラー終了する。

daemon は token cache が無いとき、または認証失敗 (`401` / `403`) を受けたときに command を再実行して token を更新する。cache は `state/tokens/*.token` に保存され、別プロセスからも再利用される。

### デプロイ要求

```bash
cd dev/deploy-broker

uv run deploy-broker-client request-deploy \
  u/michitaro/fov-quicklook-my-topic \
  --app-repo ../.. \
  --verify-mode auto
```

### 状態確認

```bash
cd dev/deploy-broker
uv run deploy-broker-client argocd-status
uv run deploy-broker-client argocd-get-branch
uv run deploy-broker-client argocd-logs coordinator

# broker 全体の smoke test
uv run deploy-broker-verify
```

`deploy-broker-client` / `deploy-broker-verify` は、明示指定が無ければ
`state/broker.key` を見て、さらに無ければ `$HOME/.keys/FOV_QUICKLOOK_BROKER_TOKEN`
を bearer token として使う。

### sync / restart

```bash
cd dev/deploy-broker

# ArgoCD sync
uv run deploy-broker-client argocd-sync

# 主要コンポーネント(coordinator, generator, frontend, debug)を再起動
uv run deploy-broker-client argocd-restart

# 特定のDeploymentだけ再起動
uv run deploy-broker-client argocd-restart coordinator
uv run deploy-broker-client argocd-restart generator frontend
```

## `argocd.sh` を使う手動運用

### 前提条件

- ArgoCD トークンが `dev/.argocd-token` に保存されていること
- トークンの有効期限は約8時間。期限切れの場合はブラウザで https://usdf-rsp-dev.slac.stanford.edu/argo-cd にログインし直してトークンを再取得する

## トークンの取得と設定

1. ブラウザで https://usdf-rsp-dev.slac.stanford.edu/argo-cd/applications/fov-quicklook にアクセス
2. 開発者ツールを開く
3. 任意のAPIリクエストを選択し「Copy as cURL」を実行
4. 以下のコマンドでトークンを抽出・保存:

```bash
cd dev
./argocd.sh extract-token "<コピーしたcurlコマンド>"
```

## Deploymentの再起動

```bash
cd dev

# 主要コンポーネント(coordinator, generator, frontend, debug)を再起動
./argocd.sh restart

# 特定のDeploymentだけ再起動
./argocd.sh restart coordinator
./argocd.sh restart generator frontend
```

## 状態確認

```bash
cd dev
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
cd dev

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
> clone / worktree 作成直後に `make setup/agent-worktree` を実行して current worktree に clone する。

ローカルの `k8s/phalanx` のブランチとArgoCDの参照ブランチが一致していない場合、設定のミスマッチが発生する。

```bash
cd dev

# 現在の参照ブランチを確認
./argocd.sh get-branch

# ブランチを変更
./argocd.sh set-branch u/michitaro/fov-quicklook-diffimage-20260311-0512

# ブランチを変更して即座にsync
./argocd.sh set-branch u/michitaro/fov-quicklook-diffimage-20260311-0512 --sync

# ローカルの Phalanx branch を確認して合わせる場合
git -C ../k8s/phalanx branch --show-current
./argocd.sh set-branch "$(git -C ../k8s/phalanx branch --show-current)" --sync
```

## ArgoCD sync

マニフェストをクラスタに適用する。ブランチ変更後やHelm valuesの更新後に使用。

```bash
cd dev
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
- `phalanx-check` / `phalanx-push` は `applications/fov-quicklook/` など許可済み path 以外を含む push を停止する
- Phalanx の安全 push は `u/michitaro/fov-quicklook-*` branch のみに制限される

## ブランチ名のルール

このタスクでは、**fov-quicklook アプリ repo** と **Phalanx repo** でルールが異なる。

### fov-quicklook アプリ repo (`lsst-sqre/fov-quicklook`)

GitHub Actions のビルドではブランチ名が Docker イメージタグに使われるため、
ブランチ名に `/` を含めないこと。

- ✗ `feature/alpha-channel` — ビルドがトリガーされない
- ✓ `feature-alpha-channel` — 正常にビルドされる

`copilot-` プレフィックスは不要。通常の説明的なブランチ名を使えばよい。

### Phalanx repo (`lsst-sqre/phalanx`)

Phalanx 側の fov-quicklook 用ブランチは、`u/michitaro/fov-quicklook-`
で始まる名前を使うこと。

- ✓ `u/michitaro/fov-quicklook-diffimage-20260311-0512`
- ✗ `copilot-by-uuid-main-20260310-2347`

`u/michitaro/fov-quicklook/...` のような `/` 区切り branch は、
remote に既存の `u/michitaro/fov-quicklook` ref があるため
Git の file/directory conflict で push できない。現状では
`u/michitaro/fov-quicklook-...` 形式を使う。

既存ブランチをリネームする場合:
```bash
git branch -m old-name new-name
git push origin -u new-name
git push origin --delete old-name
```

## 典型的なフロー

1. 標準の deploy request: `uv run deploy-broker-client request-deploy ...`
2. 参照ブランチ確認: `uv run deploy-broker-client argocd-get-branch`
3. 状態確認: `uv run deploy-broker-client argocd-status`
4. 必要なら追加 sync: `uv run deploy-broker-client argocd-sync`
5. 必要なら再起動: `uv run deploy-broker-client argocd-restart`
6. 必要ならログ確認: `uv run deploy-broker-client argocd-logs coordinator`
7. deploy 後の HTTP 検証: `./dev/verify-deploy.sh all` または broker から app token を取って直接確認
