# CI / review app

FOV-Quicklook の review app は、GitLab CI から Kubernetes へ
`build -> package -> deploy -> smoke -> stop` で展開する。
手で常駐環境を触るときは `/dev-docs/dev.ja.md`、MR ごとに使い捨て環境を作るときはこの経路を使う。

## ジョブ構成

| job | 役割 |
|---|---|
| `bootstrap:review:app` | Gateway / registry まわりの前提を整える |
| `build:review:frontend` | MR 固有の `VITE_BASE_URL` で frontend を build |
| `package:review:app` | review app 用 image を Kaniko で push |
| `review:app` | namespace と app 一式を deploy |
| `smoke:review:app` | health / visit 一覧 / quicklook 生成を確認 |
| `stop:review:app` | namespace と `HTTPRoute` を削除 |

主要な script は `ci/review-app/` にまとまっており、まとめて動かす入口は `ci/review-app/run.sh`。

## review app が起動するもの

| 要素 | 用途 |
|---|---|
| `frontend` | UI と API の入口 |
| `coordinator` | ジョブ管理と dispatch |
| `generator` | quicklook 生成 |
| `postgres` | job state |
| `minio` | `s3_tile` / `s3_test_data` |
| `seed-fixtures` job | fixture 生成、bucket 作成、Butler registry 初期化 |

review app の公開 path は既定で `/review-apps/<project-path-slug>/<mr-or-branch>`。

## shared fixture

`ci/review-app/prepare-shared-fixtures.sh` が、CI をまたいで再利用する fixture を作る。

- `dummy` datasource 用の sample FITS と manifest
- `butler` datasource 用の小さな Butler repository と env file
- `dummy.env` / `butler.env`
- fixture version marker

`butler` が既定で、catalog metadata は PostgreSQL-backed Butler registry へ流し込み、
raw FITS は `get_data_sync()` 時に仮想生成する。`dummy` に切り替えると、同じ root の sample FITS を `s3_test_data` へ同期して使う。

## よく使う入口

fixture だけ準備:

```bash
ci/review-app/run.sh fixtures \
  --root /var/tmp/fov-quicklook-review-app-fixtures \
  --visit-count 3 \
  --butler-visit-count 2000
```

build / deploy / smoke を一括実行:

```bash
ci/review-app/run.sh all
```

## 主な変数

| 変数 | 用途 |
|---|---|
| `REVIEW_APP_SHARED_FIXTURE_ROOT` | fixture の hostPath root |
| `REVIEW_APP_DATA_SOURCE` | `butler` または `dummy` |
| `REVIEW_APP_BASE_URL` | review app の公開 origin |
| `REVIEW_APP_IMAGE_REGISTRY` | image push 先 |
| `REVIEW_APP_GENERATOR_REPLICAS` | generator replica 数 |

## microk8s 開発との関係

- **共通点**: どちらも Kubernetes 上で backend / frontend / MinIO / PostgreSQL を組み合わせる
- **違い**: microk8s 開発は source tree を mount して tmux で手起動、review app CI は image を build して使い捨て namespace に配備
- **shared fixture**: dummy / butler の考え方は両方で共通。手で触るときは `/dev-docs/dev.ja.md`、自動確認はこの CI を使う
