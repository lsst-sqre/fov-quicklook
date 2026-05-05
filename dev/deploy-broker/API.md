# deploy broker API

`dev/deploy-broker/` の daemon は、fov-quicklook 専用の認証付き HTTP API を公開する。  
broker 自身が GitHub / Phalanx / ArgoCD / app access token を保持し、agent や thin client には制限した操作だけを渡す。

## ベース URL と認証

- 既定の listen address は `http://127.0.0.1:8010`
- `127.0.0.1` に bind した daemon へ `127.0.0.1` 宛てで接続する場合は bearer token 不要
- それ以外の接続では `Authorization: Bearer <broker token>` が必要
- broker token は `DEPLOY_BROKER_API_TOKEN` または `DEPLOY_BROKER_API_TOKEN_FILE` で設定できる
- client 側では `DEPLOY_BROKER_API_TOKEN_FILE` 未指定時に `state/broker.key` を見て、さらに無ければ `$HOME/.keys/FOV_QUICKLOOK_BROKER_TOKEN` を読む
- `deploy-broker-daemon` は `DEPLOY_BROKER_TOKEN_COMMAND` が未設定なら起動時にエラー終了する
- `deploy-broker-daemon` 起動時には、現在使われる broker bearer token を端末へ表示する

## token 取得の挙動

- `DEPLOY_BROKER_TOKEN_COMMAND` に設定したコマンドを `shlex.split` で解釈して実行する
- 標準出力は次の JSON object を前提にする

```json
{"argocd_token": "ARGOCD_TOKEN", "gafaelfawr_token": "GAFAELFAWR_TOKEN"}
```

- 取得した token は state dir 配下の `tokens/argocd.token` と `tokens/app.token` にキャッシュする
- token file は別プロセスからも再利用され、cache miss / refresh 時は lock file で排他して token command の多重実行を避ける
- token cache が無いときに初回取得する
- ArgoCD API または app verification で `401` / `403` を受けた場合、token command を再実行して cache を更新し、同じ操作を 1 回だけ再試行する

## Phalanx change policy

- `DEPLOY_BROKER_PHALANX_CHANGE_POLICY` で Phalanx 側の変更許可範囲を設定する
- 利用可能な mode:
  - `fov-quicklook-paths`: 既定値。`applications/fov-quicklook/` など既存 allowlist path 配下の変更を許可
  - `values-yaml-only`: `applications/fov-quicklook/values.yaml` への変更だけを許可
  - `image-tag-only`: `applications/fov-quicklook/values.yaml` の `image.tag` 行変更だけを許可
- 判定は `origin/main` からの差分を基準に行い、未コミット差分も含めて検証する
- stricter mode ほど imported Phalanx bundle の変更を通しにくくなり、broker が付与する image tag 更新だけを通したい運用に向く

## エラーハンドリング

- `ValueError` は HTTP `400`
- `RuntimeError` は HTTP `503`
- その他の未分類例外は HTTP `500`
- `GET /v1/deploy-requests/{request_id}` で対象が無い場合は HTTP `404`

## エンドポイント一覧

| Method | Path | 認証 | 用途 |
| --- | --- | --- | --- |
| `GET` | `/healthz` | 不要 | broker 自身のヘルスチェック |
| `GET` | `/v1/tokens/app` | 必要 | app access token を取得 |
| `GET` | `/v1/argocd/status` | 必要 | fov-quicklook 各 Deployment の ready 状態と image を取得 |
| `GET` | `/v1/argocd/branch` | 必要 | ArgoCD が参照中の Phalanx repo / path / branch を取得 |
| `GET` | `/v1/argocd/logs/{component}` | 必要 | 指定 component の Pod ログを取得 |
| `POST` | `/v1/argocd/sync` | 必要 | ArgoCD sync を実行 |
| `POST` | `/v1/argocd/restart` | 必要 | 指定 Deployment を再起動 |
| `POST` | `/v1/deploy-requests` | 必要 | deploy request を enqueue |
| `GET` | `/v1/deploy-requests/{request_id}` | 必要 | deploy request の進捗と結果を取得 |

## レスポンス仕様

### `GET /healthz`

```json
{"status": "ok"}
```

### `GET /v1/tokens/app`

```json
{"token": "<gafaelfawr token>"}
```

### `GET /v1/argocd/status`

```json
{
  "deployments": [
    {
      "deployment": "fov-quicklook-frontend",
      "ready_replicas": "2",
      "replicas": "2",
      "image": "ghcr.io/lsst-sqre/fov-quicklook:main"
    }
  ]
}
```

取得に失敗した Deployment は `ready_replicas="?"`、`replicas="?"`、`image="取得失敗"` で返る。

### `GET /v1/argocd/branch`

```json
{
  "repo": "https://github.com/lsst-sqre/phalanx.git",
  "path": "applications/fov-quicklook",
  "branch": "main"
}
```

### `GET /v1/argocd/logs/{component}`

- `component` は `coordinator` / `generator` / `frontend` / `db` / `debug` または `fov-quicklook-*`
- query parameter: `since_seconds`（既定 `600`）

```json
{
  "component": "coordinator",
  "pod_name": "fov-quicklook-coordinator-abc123",
  "logs": "...\n"
}
```

### `POST /v1/argocd/sync`

```json
{"synced": true}
```

### `POST /v1/argocd/restart`

request body:

```json
{"components": ["frontend", "generator"]}
```

`components` を空配列または省略相当で送ると、既定で `coordinator` / `generator` / `frontend` / `debug` を再起動する。

response:

```json
{"restarted": ["fov-quicklook-frontend", "fov-quicklook-generator"]}
```

### `POST /v1/deploy-requests`

`multipart/form-data` で送る。

必須 form field:

- `tracked_branch`
- `verify_mode` (`none` / `auto` / `all`)
- `app_branch_name`
- `app_head_sha`
- `app_bundle`

任意 form field:

- `app_base_sha`
- `phalanx_branch_name`
- `phalanx_head_sha`
- `phalanx_base_sha`
- `phalanx_bundle`

response は `DeployRequestRecord`:

```json
{
  "request_id": "4f6d...",
  "status": "queued",
  "tracked_branch": "u/michitaro/fov-quicklook-example",
  "verify_mode": "auto",
  "build_branch": null,
  "app_commit_sha": null,
  "phalanx_commit_sha": null,
  "app_branch_name": "feature/example",
  "phalanx_branch_name": null,
  "image_tag": null,
  "run_id": null,
  "step": null,
  "error": null,
  "logs": [],
  "verification": null
}
```

### `GET /v1/deploy-requests/{request_id}`

返却 shape は `POST /v1/deploy-requests` と同じ `DeployRequestRecord`。  
進行中は `status=queued|running`、完了後は `status=succeeded|failed`。`logs` には timestamp 付き進捗ログが追加される。

## deploy request の内部ステップ

`step` にはおおむね次の値が入る。

- `preparing`
- `importing-bundles`
- `building`
- `materializing-phalanx`
- `argocd-sync`
- `verification`
- `complete`
- `failed`

## state dir の主な保存物

- `broker.key`
- `tokens/argocd.token`
- `tokens/app.token`
- `jobs/*.json`
- `repos/`
- `requests/`

## 実機向け動作確認 CLI

`deploy-broker-verify` は deploy broker 実行マシンまたは localhost / SSH tunnel 越しの thin client から、broker の各機能を順に叩いて smoke test するための CLI。

- 既定では read-only な確認だけを行う
  - `GET /healthz`
  - `GET /v1/tokens/app`
  - `GET /v1/argocd/status`
  - `GET /v1/argocd/branch`
  - `GET /v1/argocd/logs/{component}`
- `--include-sync` を付けると `POST /v1/argocd/sync` も実行する
- `--restart-components ...` を付けると `POST /v1/argocd/restart` も実行する
- `--deploy-tracked-branch ... --app-repo ...` を付けると `POST /v1/deploy-requests` と `GET /v1/deploy-requests/{request_id}` も実行する

例:

```bash
cd dev/deploy-broker

# read-only smoke test
uv run deploy-broker-verify

# sync / restart を含める
uv run deploy-broker-verify --include-sync --restart-components frontend

# deploy request まで含めて完走確認
uv run deploy-broker-verify \
  --deploy-tracked-branch u/michitaro/fov-quicklook-verify-20260505 \
  --app-repo ../.. \
  --verify-mode auto
```

`--deploy-tracked-branch` は実際に build / Phalanx push / ArgoCD sync を伴うため、検証用 branch だけで使うこと。
