# FOV-Quicklook Phalanx デプロイメント ガイド

## 概要

FOV-Quicklook は [Phalanx](https://phalanx.lsst.io) を使用して Kubernetes にデプロイされます。Phalanx は Rubin Observatory の Kubernetes プラットフォームで、Argo CD を使用したGitOpsベースのデプロイメントを提供します。

## ディレクトリ構造

```
k8s/
  helmchart -> ./phalanx/applications/fov-quicklook/  # シンボリックリンク
  phalanx/
    applications/
      fov-quicklook/
        .helmignore
        Chart.yaml                 # Helm チャートメタデータ
        README.md                  # 自動生成された Values ドキュメント
        secrets.yaml               # Vault シークレット定義
        templates/
          _helpers.tpl             # 共通テンプレートヘルパー
          butler-config.yaml       # Butler リポジトリ設定 ConfigMap
          coordinator.yaml         # コーディネーター Deployment/Service/NetworkPolicy
          db.yaml                  # PostgreSQL StatefulSet/Service
          debug.yaml               # デバッグ用設定（オプション）
          frontend.yaml            # フロントエンド Deployment/Service/Ingress
          generator.yaml           # ジェネレーター Deployment/Service
          vault-secrets.yaml       # Vault 統合用 ExternalSecret
        values.yaml                # デフォルト設定値
        values.schema.json         # values.yaml のJSONスキーマ
        values-usdfdev.yaml        # USDF 開発環境用オーバーライド
        values-usdfprod.yaml       # USDF 本番環境用オーバーライド
```

## 主要な Values 設定

### イメージ設定

```yaml
image:
  repository: ghcr.io/lsst-sqre/fov-quicklook
  pullPolicy: Always
  tag: main
```

### 認証・シークレット

```yaml
use_vault: true      # Vault でシークレットを管理
use_gafaelfawr: true # Gafaelfawr で認証
```

### S3 タイルストレージ

```yaml
s3_tile:
  endpoint: sdfembs3.sdf.slac.stanford.edu:443
  secure: true
  bucket: fov-quicklook-tile

config:
  s3_tile_path_prefix: "fov-quicklook/prod"
  max_object_storage_usage: 100_000_000_000  # 100GB
```

### リソース設定

各コンポーネントのリソース制限を設定できます：

```yaml
coordinator:
  resources:
    requests: { cpu: 100m, memory: 512Mi }
    limits: { cpu: 4000m, memory: 512Mi }

generator:
  replicas: 8
  concurrency: 20
  resources:
    requests: { cpu: 2000m, memory: 8Gi }
    limits: { cpu: 12000m, memory: 8Gi }
  local_storage:
    sizeLimit: 32Gi

frontend:
  replicas: 2
  resources:
    requests: { cpu: 100m, memory: 512Mi }
    limits: { cpu: 8000m, memory: 512Mi }

db:
  resources:
    requests: { cpu: 100m, memory: 256Mi }
    limits: { cpu: 2000m, memory: 256Mi }
```

### Butler 設定

```yaml
butler_settings:
  envs:
    - name: DAF_BUTLER_REPOSITORY_INDEX
      value: /var/run/fov-quicklook/config/data-repos.yaml
    - name: AWS_SHARED_CREDENTIALS_FILE
      value: /var/run/fov-quicklook/secrets/aws-credentials.ini
    - name: PGUSER
      value: rubin
    # ... その他の環境変数
  volumes: [...]
  volume_mounts: [...]
  data_repos:
    embargo: s3://embargo@rubin-summit-users/butler.yaml
```

### CCD データタイプ設定

```yaml
ccd_data_types:
  - name: raw
    display_name: Raw
    collections:
      - LSSTCam/raw/all
    data_id_dimension: exposure
    order_by:
      - -day_obs
      - -exposure
    partial: false
  - name: post_isr_image
    display_name: Post-ISR
    collections:
      - LSSTCam/runs/nightlyValidation
    data_id_dimension: exposure
    order_by:
      - -exposure
    partial: true
  - name: difference_image
    display_name: Difference Image
    collections:
      - LSSTCam/runs/nightlyValidation
    data_id_dimension: visit
    order_by:
      - -visit
    partial: true
  - name: preliminary_visit_image
    display_name: Preliminary
    collections:
      - LSSTCam/runs/nightlyValidation
    data_id_dimension: visit
    order_by:
      - -visit
    partial: true
```

## シークレット管理

`secrets.yaml` で Vault から取得するシークレットを定義：

| シークレットキー | 説明 |
|------------------|------|
| `db_password` | PostgreSQL データベースパスワード |
| `s3_repository_access_key` | S3 タイルストレージ アクセスキー |
| `s3_repository_secret_key` | S3 タイルストレージ シークレットキー |
| `aws-credentials.ini` | Butler 用 AWS 認証情報 |
| `postgres-credentials.txt` | Butler 用 PostgreSQL 認証情報 |

## テンプレートヘルパー

`_helpers.tpl` で定義されている共通テンプレート：

| ヘルパー名 | 説明 |
|-----------|------|
| `fov-quicklook.env.s3_tile` | S3 タイル関連の環境変数 |
| `fov-quicklook.env.db` | データベース接続環境変数 |
| `fov-quicklook.env.log-level` | ログレベル環境変数 |
| `fov-quicklook.butler-settings.env` | Butler 設定環境変数 |
| `quicklook.ingress.spec` | Ingress ルール定義 |

## 環境別設定

### USDF 開発環境 (`values-usdfdev.yaml`)

開発・テスト用の設定。通常はリソース制限が緩和されている。

### USDF 本番環境 (`values-usdfprod.yaml`)

本番運用用の設定。安定性とパフォーマンスを重視。

## デプロイワークフロー

このリポジトリでは、`dev/` 配下の deploy ツールを使って **fov-quicklook だけ** を対象に安全にデプロイする。

### 前提条件

- trusted maintainer 用マシンであること
- app repo (`lsst-sqre/fov-quicklook`) への push 権限があること
- `k8s/phalanx/` に `lsst-sqre/phalanx` を clone 済みであること
- broker の state dir に ArgoCD token / app token が登録済みであること

### 標準手順

```bash
# app repo は commit 済みの branch を使う
git branch --show-current

# agent-safe な deploy request を broker に送る
cd dev/deploy-broker
uv run deploy-broker-client request-deploy \
  u/michitaro/fov-quicklook-diffimage-20260311-0512 \
  --app-repo ../.. \
  --verify-mode auto
```

`deploy-broker-client request-deploy` は次をまとめて実行する。

1. app repo の commit を `git bundle` 化して broker に送る
2. broker が `fov-quicklook-local-*` build branch に push
3. GitHub Actions `build-and-push.yml` の完了待ち
4. broker が `k8s/phalanx/applications/fov-quicklook/values.yaml` の `image.tag` を更新して push
5. broker が ArgoCD の branch 切り替えと sync を実行
6. app token を使った HTTP 動作確認を agent / operator が直接行う

### agent-safe な broker フロー

agent に GitHub / ArgoCD の直接権限を渡したくない場合は、`dev/deploy-broker/`
配下の broker daemon を使う。broker は認証付き HTTP API を公開し、次を担当する。

1. app repo の `git bundle` と必要なら Phalanx bundle の受け取り
2. dedicated deploy 権限での GitHub build branch push と build 完了待ち
3. Phalanx branch の materialization と image tag 更新
4. ArgoCD の branch 切り替え、必要な `image.tag` override 更新、sync
5. ArgoCD status / branch / logs の安全に制限された取得
6. ArgoCD sync / Deployment restart の安全に制限された実行

ArgoCD token は broker 側だけが保持し、agent には返さない。app access token は
broker 側で保持し、agent は必要時に broker から受け取って `healthz` などの
一般ユーザー向け HTTP 検証に使う。

#### 開発時のローカル起動

開発中は broker をひとまずローカルで起動してよい。ArgoCD token と app token は
**daemon ノード側の state dir** に置いた bootstrap file から、**daemon 起動時**に取り込む。

```bash
mkdir -p dev/deploy-broker/state/bootstrap

# daemon ノード側で Copy as cURL をそのまま保存しておく
$EDITOR dev/deploy-broker/state/bootstrap/argocd.curl
$EDITOR dev/deploy-broker/state/bootstrap/app.curl

cd dev/deploy-broker

# ローカル daemon を起動
# 起動時に state/bootstrap/*.curl を読んで tokens/*.token に保存し、元ファイルは削除する
uv run deploy-broker-daemon

# 別ターミナルで
# broker 経由で app token を取得
uv run deploy-broker-client get-app-token

# app repo の現在 branch を bundle 化して deploy request を送る
uv run deploy-broker-client request-deploy \
  u/michitaro/fov-quicklook-my-topic \
  --app-repo ../.. \
  --verify-mode none
```

client は **`http://127.0.0.1:8010` をデフォルト接続先**とする。daemon が
`127.0.0.1` bind の場合は、**broker token は不要**である。broker token
(`broker.key` / `DEPLOY_BROKER_API_TOKEN`) は、broker を non-loopback に
公開するときだけ使う。

#### broker の監査ログ

broker daemon は state dir 配下に永続ログを残す。

| パス | 用途 |
|---|---|
| `state/logs/broker-audit.jsonl` | daemon 起動/停止、HTTP request、`argocd sync` / `restart`、deploy request の受理・成功・失敗などの監査ログ |
| `state/requests/<request_id>/broker.log` | 1 deploy request ごとの詳細ログ。step 遷移、git / gh command 実行、build / ArgoCD / verification の詳細を残す |
| `state/jobs/<request_id>.json` | client が poll する軽量ステータス。`logs[]` は progress 要約で、詳細は `request_log_path` を参照する |

監査ログは 1 行 1 JSON の JSONL 形式で保存する。現在の broker 認証は shared bearer token
なので、**誰が** の識別は当面 `remote host` と `auth_mode`（`bearer` /
`loopback-bypass`）が上限である。

token / cookie / Authorization header / bundle 本体はログに残さない。command 失敗時の
stdout / stderr は必要な範囲で要約して記録し、secret 文字列はマスクする。

必要に応じて以下でローテーション設定を変えられる。

```bash
export DEPLOY_BROKER_LOG_LEVEL=DEBUG
export DEPLOY_BROKER_LOG_MAX_BYTES=10000000
export DEPLOY_BROKER_LOG_BACKUP_COUNT=10
```

#### 別サーバーで broker daemon を動かす

別サーバー運用では、broker daemon を **trusted user** で常駐させ、そのホストだけに
GitHub push / GitHub Actions / ArgoCD token / app token を持たせる。

##### ノードごとの権限分離

現行実装では、**thin client / agent ノード** と **broker daemon ノード** の責務は次のように分かれる。

| ノード | 必要な権限・設定 | 不要なもの |
|---|---|---|
| thin client / agent ノード | app repo の checkout、`deploy-broker-client`、daemon node の `127.0.0.1:8010` へ届く経路（通常は SSH tunnel） | `gh auth`、app repo への `git push`、Phalanx への `git push`、ArgoCD token、app token |
| broker daemon ノード | `gh auth`、app repo build branch (`fov-quicklook-local-*`) への `git push`、Phalanx tracked branch (`u/michitaro/fov-quicklook-*`) への `git push`、ArgoCD token / app token の保存、daemon 用 state dir (`bootstrap/*.curl` または `tokens/*.token`) | agent 側の作業ツリーや editor |

つまり、**agent 用ノードは app repo に `git push` できなくてよい**。その代わり、
**broker daemon ノードは app repo の build branch に push できる必要がある**。
現在の broker は app repo への push をトリガーに GitHub Actions `build-and-push.yml`
を起動するため、この権限は daemon 側では必須である。

もし **broker daemon ノードにも app repo push 権限を持たせたくない**場合は、
`workflow_dispatch` など別の build trigger を使う再設計が必要で、現行実装の範囲外。

##### サーバー側の前提

- `git` / `gh` / `uv` が使えること
- app repo の build branch と Phalanx tracked branch へ HTTPS で push できること
- `gh auth status` が成功し、`repo` と `workflow` scope を持つこと
- `gh auth setup-git` 済みで、`git push https://github.com/...` が `gh` の credential を使えること
- `git config user.name` / `git config user.email` が設定済みであること（Phalanx commit 用）
- ArgoCD API (`https://usdf-rsp-dev.slac.stanford.edu/argo-cd`) へ HTTPS で到達できること

##### サーバー側の初期セットアップ

```bash
# 任意の作業ディレクトリに repo を clone
git clone https://github.com/lsst-sqre/fov-quicklook.git /srv/fov-quicklook

cd /srv/fov-quicklook/dev/deploy-broker
uv sync --extra dev

# GitHub / git push に使う認証を準備
gh auth login --hostname github.com
gh auth setup-git
gh auth status

# Phalanx commit 用の identity
git config --global user.name "fov-quicklook deploy broker"
git config --global user.email "your-account@users.noreply.github.com"
```

##### broker API 認証

標準運用では、daemon は **`127.0.0.1:8010` に listen** し、thin client は
SSH tunnel などで **自分の `127.0.0.1:8010`** に届くようにして使う。
この **localhost 接続では broker token は不要**である。

broker token が必要なのは、broker を private network 上の non-loopback address へ
直接 expose するときだけである。その場合は `broker.key` を作り、client 側で
`DEPLOY_BROKER_API_TOKEN` または `DEPLOY_BROKER_API_TOKEN_FILE` を設定する。

```bash
# 例: direct HTTP 用に token を作る場合だけ broker.key を置く
mkdir -p /srv/fov-quicklook-broker-state
cd /srv/fov-quicklook-broker-state
openssl rand -base64 32 > broker.key
chmod 600 broker.key
```

##### daemon の起動設定

別サーバーでは、**daemon の WorkingDirectory を repo 外の state dir にする**。
listen host の default は **`127.0.0.1`** なので、通常は host の指定は不要。

```bash
cd /srv/fov-quicklook-broker-state

# daemon ノード側で token bootstrap file を配置しておく
mkdir -p bootstrap
$EDITOR bootstrap/argocd.curl
$EDITOR bootstrap/app.curl

# 起動時に bootstrap/*.curl を読んで tokens/*.token に保存し、元ファイルは削除する
uv run --project /srv/fov-quicklook/dev/deploy-broker deploy-broker-daemon
```

- default のままで broker は `127.0.0.1:8010` に bind する
- 別ホストから直接叩くなら private network の address を bind し、firewall か reverse proxy で保護する
- 現在の broker は TLS を内蔵していないため、インターネットに直接 expose しない

##### thin client からの接続方法

ここでいう **SSH tunnel** は、remote server 上の `127.0.0.1:8010` を thin client 側の
`127.0.0.1:8010` に転送する **SSH port forward** のこと。broker の必須機能ではなく、
**localhost bind の daemon に安全に届くための接続方法の一例**である。

broker 自身の認証は SSH ではなく broker API の allowlist と bind address で守る。
**`127.0.0.1` 宛ての接続では broker token は不要**で、SSH tunnel を使う標準運用もこれに含まれる。
broker token が必要なのは、broker を non-loopback address へ直接 expose する場合だけである。

**例1: daemon を `127.0.0.1` bind のまま使う場合**

```bash
# thin client 側
ssh -N -L 8010:127.0.0.1:8010 broker-host.example.org

uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-status

uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  request-deploy \
  u/michitaro/fov-quicklook-my-topic \
  --app-repo /path/to/your/fov-quicklook \
  --verify-mode auto
```

**例2: broker を private network 上で listen させ、直接 HTTP でつなぐ場合**

この場合は SSH tunnel は不要。ただし broker port をそのまま expose することになるので、
private network に閉じる、firewall で絞る、reverse proxy / TLS を前段に置く、などは
別途考える必要がある。

```bash
export DEPLOY_BROKER_API_TOKEN_FILE=/path/to/your/broker-state/broker.key

uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  --server http://broker-host.example.org:8010 \
  argocd-get-branch
```

##### daemon 起動時の token bootstrap

ArgoCD token と app token の**登録は daemon ノード側で行う**。`deploy-broker-client`
から broker に token を送ることはしない。

daemon は起動時に state dir 配下の以下を探し、存在すれば cURL 文字列から token を抽出して
`tokens/*.token` に保存する。取り込み後、元の `*.curl` file は削除する。

- `bootstrap/argocd.curl`
- `bootstrap/app.curl`

```bash
# daemon host 側
cd /srv/fov-quicklook-broker-state
mkdir -p bootstrap

cat > bootstrap/argocd.curl <<'EOF'
curl 'https://usdf-rsp-dev.slac.stanford.edu/argo-cd/api/v1/applications/fov-quicklook' \
  -H 'Cookie: argocd.token=...'
EOF

cat > bootstrap/app.curl <<'EOF'
curl 'https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/api/healthz' \
  -H 'Cookie: gafaelfawr="..."'
EOF

# 前景で起動する。client 操作は別ターミナルから行う
uv run --project /srv/fov-quicklook/dev/deploy-broker deploy-broker-daemon
```

保存先は state dir 配下の以下。

- `tokens/argocd.token`
- `tokens/app.token`
- `jobs/*.json` - deploy job status
- `repos/` - daemon 側の cached clone
- `requests/` - bundle と per-request workspace

##### systemd で常駐させる例

```ini
[Unit]
Description=fov-quicklook deploy broker
After=network-online.target
Wants=network-online.target

[Service]
User=fovquicklook
WorkingDirectory=/srv/fov-quicklook-broker-state
ExecStart=/usr/local/bin/uv run --project /srv/fov-quicklook/dev/deploy-broker deploy-broker-daemon
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`ExecStart` の `uv` の path は実際のインストール先に合わせて変更する。

### 手動で分けて実行したい場合

```bash
cd /path/to/your/broker-state

# daemon 側で token bootstrap file を配置してから daemon を起動
mkdir -p bootstrap
$EDITOR bootstrap/argocd.curl
$EDITOR bootstrap/app.curl

# このコマンドは前景で動くので、以降は別ターミナルで実行する
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-daemon

# broker 経由の状態確認
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-status
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-get-branch

# broker 経由の sync / restart
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-sync
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-restart debug

# deploy request
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  request-deploy \
  u/michitaro/fov-quicklook-diffimage-20260311-0512 \
  --app-repo /path/to/your/fov-quicklook

# broker 経由のログ確認
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  argocd-logs coordinator

# broker 自身の監査ログ
tail -f /path/to/your/broker-state/logs/broker-audit.jsonl

# request_id ごとの詳細ログ
tail -f /path/to/your/broker-state/requests/<request_id>/broker.log

# app token を取って直接 HTTP 確認
uv run --project /path/to/your/fov-quicklook/dev/deploy-broker deploy-broker-client \
  get-app-token
./verify-deploy.sh all
```

### ブランチ名のルール

- app repo の branch は `/` を含めない
- Phalanx branch は `u/michitaro/fov-quicklook-*`
- broker が作る build branch は `fov-quicklook-local-*`

### 安全性

`dev/deploy-broker/` は次を検証または強制する。

- ArgoCD の対象 application が `fov-quicklook` であること
- ArgoCD の source path が `applications/fov-quicklook` であること
- Phalanx push branch が `u/michitaro/fov-quicklook-*` であること
- push 対象ファイルが `applications/fov-quicklook/` など許可済み path のみであること
- ArgoCD token を daemon 内に閉じ込めること
- sync / restart の操作対象を `fov-quicklook` 配下の Deployment に限定すること
- stale な ArgoCD `image.tag` override が残っていても、新しい deploy tag に更新すること

このため、broker 経由の deploy フローでは他 application への accidental push を避けやすい。

`dev/deploy-broker/` は同じ制約を broker 側の構造化コードに取り込み、agent からは
認証付き HTTP API だけを見せることで、GitHub / ArgoCD への直接アクセスを避ける。

## トラブルシューティング

### ポッドのログを確認

```bash
kubectl -n fov-quicklook logs pod/<pod-name> --tail=100
```

### シークレットの確認

```bash
kubectl -n fov-quicklook get secrets fov-quicklook -o yaml
```

### Helm テンプレートのデバッグ

```bash
cd k8s/helmchart
helm template . --debug --values values.yaml 2>&1 | less
```

## 関連ドキュメント

- [Phalanx 公式ドキュメント](https://phalanx.lsst.io)
- [Argo CD ドキュメント](https://argo-cd.readthedocs.io/)
- [Helm チャート開発ガイド](https://helm.sh/docs/chart_template_guide/)
- `dev/deploy-broker/`
- `dev/argocd.sh`
- `dev/verify-deploy.sh`
