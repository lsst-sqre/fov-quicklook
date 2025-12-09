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
    data_id_key: exposure
    order_by:
      - -day_obs
      - -exposure
    partial: false
  - name: post_isr_image
    display_name: Post-ISR
    collections:
      - LSSTCam/runs/nightlyValidation
    data_id_key: exposure
    order_by:
      - -exposure
    partial: true
  - name: preliminary_visit_image
    display_name: Preliminary
    collections:
      - LSSTCam/runs/nightlyValidation
    data_id_key: visit
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

1. **変更の準備**: `k8s/helmchart/` 内の設定ファイルを編集

2. **ローカルテスト**:
   ```bash
   cd k8s/helmchart
   helm template . --values values.yaml
   ```

3. **Phalanx へのプッシュ**:
   
   FOV-Quicklook の Phalanx 設定は `lsst-sqre/phalanx` リポジトリに存在します。
   変更を加えるには：
   
   1. `lsst-sqre/phalanx` リポジトリをクローン
   1. `applications/fov-quicklook/` 内のファイルを更新
   1. プルリクエストを作成

4. **デプロイ**:
   
   Argo CD が変更を検知し、自動的にデプロイします。

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
