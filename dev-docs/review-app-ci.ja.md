# CI review app

## 概要

FOV-Quicklook の review app は、GitLab CI から Kubernetes 上へ `build -> package -> deploy -> smoke -> stop` で展開できる。

現状の実装では次を行う。

- `.gitlab-ci.yml` に review app 専用 job を追加
- `ci/review-app/` で namespace / image / URL / deploy / cleanup を管理
- `frontend` / `coordinator` / `generator` / `PostgreSQL` / `MinIO` を MR ごとの namespace に起動
- 共有 fixture root に置いた sample FITS / Butler repository を `dummy` または `butler` で使い回す
- Gateway API の `HTTPRoute` で MR 固有 URL を払い出す
- deploy 後に visit 一覧と quicklook 生成まで smoke check する

既定の `REVIEW_APP_DATA_SOURCE` は `butler` である。前段で追加した shared fixture がそのまま使えるため、review app でも sample data と Butler repository を CI 間で再利用できる。
現在の `butler` fixture は、約 2000 exposure の catalog metadata を PostgreSQL-backed Butler registry へ流し込み、実際の raw FITS は `DataSource.get_data_sync()` で添付画像ベースにオンザフライ生成する。review app で使う CCD は画面中央の 9 枚 (`R22_S00..S22`) に絞り、サンプル画像は `180` 度回転したうえでその 3x3 領域へ bilinear で引き伸ばしている。

## 構成

### CI job

| job | 役割 |
| --- | --- |
| `bootstrap:review:app` | Gateway と cluster 内 registry の接続情報を整える |
| `build:review:frontend` | MR 固有 `VITE_BASE_URL` で frontend を build する |
| `package:review:app` | review app 専用 Docker image を Kaniko で push する |
| `review:app` | Kubernetes へ deploy し、review app URL を environment に返す |
| `smoke:review:app` | visit 一覧と quicklook 生成を確認する |
| `stop:review:app` | `HTTPRoute` と namespace を削除する |

### Pod / Service

| 要素 | 用途 | ストレージ |
| --- | --- | --- |
| `frontend` | UI と API の入口 | image 内の `frontend-assets` + shared fixture mount |
| `coordinator` | ジョブ管理、DB bootstrap、generator dispatch | shared fixture mount |
| `generator` | quicklook 生成 | shared fixture mount + `emptyDir` |
| `postgres` | job state 永続化 | `emptyDir` |
| `minio` | `s3_tile` / `s3_test_data` | `emptyDir` |
| `seed-fixtures` job | fixture 生成・bucket 作成・必要なら dummy sample seed | shared fixture hostPath |

shared fixture root は host 側の永続 path に置き、Pod から**同じ絶対 path**へ mount する。これにより `butler.env` の `DAF_BUTLER_REPOSITORY_INDEX` と `data-repos.yaml` を書き換えずに再利用できる。
review app deploy 時は `seed-fixtures` job の init container が namespace 内 PostgreSQL の `butler_registry` DB を初期化し、その後の fixture job が Butler catalog を流し込む。

### 公開 URL

review app の base path は既定で次になる。

`/review-apps/<project-path-slug>/<mr-or-branch>`

frontend build の `VITE_BASE_URL` と backend の `frontend_app_prefix` はこの path で揃える。`HTTPRoute` は rewrite せず、そのまま `frontend` Service へ流す。

## 必要な CI 変数

| 変数 | 用途 |
| --- | --- |
| `REVIEW_APP_KUBECONFIG_B64` | runner 既定 kubeconfig を使わない場合の kubeconfig |
| `REVIEW_APP_GATEWAY_ADDRESS` | review app 公開 IP。未設定時は node InternalIP を自動検出 |
| `REVIEW_APP_BASE_URL` | review app 公開 URL の origin。未設定時は `http://<gateway-address>` |
| `REVIEW_APP_IMAGE_REGISTRY` | Kaniko の push 先 registry。未設定時は `<gateway-address>:32000` |
| `REVIEW_APP_SHARED_FIXTURE_ROOT` | shared fixture hostPath root。未設定時は `/var/tmp/fov-quicklook-review-app-fixtures` |
| `REVIEW_APP_DATA_SOURCE` | `butler` または `dummy`。既定は `butler` |
| `REVIEW_APP_DUMMY_VISIT_COUNT` | materialize する dummy visit 数。既定は `3` |
| `REVIEW_APP_BUTLER_VISIT_COUNT` | Butler catalog に入れる exposure 数。既定は `2000` |
| `REVIEW_APP_GENERATOR_REPLICAS` | generator replica 数。既定は `2` |

## 使い方 / 構築手順

`ci/review-app/run.sh` は既存 script 群を薄く束ねた wrapper で、まとめて実行したいときの入口として使える。

### fixture だけ準備

```bash
ci/review-app/run.sh fixtures \
  --root /var/tmp/fov-quicklook-review-app-fixtures \
  --visit-count 3 \
  --butler-visit-count 2000
```

### review app を一括で build / deploy / smoke

```bash
ci/review-app/run.sh all
```

個別に動かしたい場合は、引き続き `bootstrap-gateway.sh` / `package.sh` / `deploy.sh` / `smoke.sh` / `stop.sh` を直接使える。

## 現状確認

### アプリ側ですでに使えるもの

- `frontend/app/vite.config.ts` は `VITE_BASE_URL` を受け取り、Vite build の `base` を切り替えられる
- `frontend/app/src/App.tsx` は `BrowserRouter basename={env.baseUrl}` を使っている
- `backend/src/quicklook/frontend/api/app.py` と `staticassets.py` は `config.frontend_app_prefix` 配下で API と SPA 配信を行う
- `backend/src/quicklook/config/__init__.py` により、データソースは `butler` / `dummy` を切り替えられる
- `dummy` データソースでも、実際には `config.s3_test_data` から FITS を読むため、sample data 用の S3/MinIO は必要である
- ジョブ状態は `config.db_url` の PostgreSQL に保存されるため、review app でも DB は必要である

### この実装で追加したもの

- `.gitlab-ci.yml`
- `ci/review-app/common.sh`
- `ci/review-app/bootstrap-gateway.sh`
- `ci/review-app/package.sh`
- `ci/review-app/deploy.sh`
- `ci/review-app/smoke.sh`
- `ci/review-app/stop.sh`
- `ci/review-app/run.sh`
- `ci/review-app/Dockerfile`
- `ci/review-app/entrypoint.sh`

## shared fixture とのつなぎ方

review app deploy では `seed-fixtures` job が `python -m quicklook.review_app.shared_fixtures` を実行し、shared fixture root を必要に応じて生成・更新する。

- `butler` のときは shared root 配下の `butler.env` を `ENV_FILE` に使う
- `dummy` のときは `dummy.env` を `ENV_FILE` に使い、同じ job で `s3_test_data` へ sample FITS を seed する
- `butler` のときは同じ job で `--butler-registry-url postgresql://.../butler_registry` を渡し、Butler metadata を namespace 内 PostgreSQL に再生成する
- どちらの場合でも `--ensure-tile-bucket` で `s3_tile` bucket を先に作る

これにより、fixture のバージョン管理は Python 側に寄せたまま、CI では deploy 前に 1 job 呼ぶだけで済む。

## 実装メモ

### 1. CI 共通基盤

`cmos-reader2` の review app 実装をそのまま流用できる部分が多い。

- MR ごとに一意な namespace を作る仕組み
- `bootstrap -> build/package -> deploy -> stop` の job 分離
- CI から使える `kubectl` 実行環境
- cluster から pull できる container registry
- review app の公開 URL を作る `Gateway` / `Ingress`
- MR close 後または manual stop 時に namespace を片付ける cleanup job

`cmos-reader2` の review app 構成を下敷きにしているが、FOV-Quicklook では viewer を別 service に分けず、単一の `frontend` へ base path ごと流す構成に簡略化している。

### 2. FOV-Quicklook アプリ実行に必要な Pod/Service

review app でも最低限次が必要になる。

| 要素 | 用途 | 備考 |
| --- | --- | --- |
| `frontend` | UI と REST API の入口 | base path 配下で公開 |
| `coordinator` | ジョブ管理、generator への RPC dispatch | 単一 Pod 前提 |
| `generator` | タイル生成 | review app では既定 2 Pod |
| `PostgreSQL` | ジョブ状態永続化 | review app ごとに分離 |
| `S3/MinIO` (`tile`) | 生成済み PackedTiles の保存 | 必須 |
| `S3/MinIO` (`test_data`) | sample FITS 配布 | `dummy` のときのみ seed する |

加えて、`generator` の一時作業領域として `emptyDir` などのローカルストレージも必要になる。

### 3. sample data

review app の価値を出すには、最低でも quicklook を 1 件以上生成できる sample data が必要である。

review app は `dummy` / `butler` の両方に対応している。

| 構成 | sample data の置き場所 | 現在の扱い |
| --- | --- | --- |
| `dummy` | `s3_test_data` バケット | `seed-fixtures` job が MinIO へ manifest/FITS を投入 |
| `butler` | shared fixture root 配下の Butler repo + namespace 内 PostgreSQL registry | 既定。metadata は PostgreSQL、raw FITS は on-demand 生成 |

`dummy` でも `raw/<visit>/<ccd>.fits` 形式など、`backend/src/quicklook/datasource/dummy_datasource/__init__.py` が期待する配置で FITS を置く必要がある。
したがって「sample data は不要」ではなく、「Butler を使わないなら、軽量な S3 配置で済む」が正しい整理になる。

### 4. Butler を使う場合に追加で必要なもの

`Butler` 構成まで review app に入れる場合、次が追加で必要になる。

- `DAF_BUTLER_REPOSITORY_INDEX`
- `AWS_SHARED_CREDENTIALS_FILE`
- `PGPASSFILE` または同等の PostgreSQL 認証情報
- `repository_name` / `instrument` / `collections` を含む `ccd_data_types` 設定
- review app から参照できる小さな Butler repository
- その repository が参照する PostgreSQL と S3 認証情報

`backend/src/quicklook/datasource/butler_datasource/__init__.py` と `backend/src/quicklook/datasource/butler_datasource/README.md` を見る限り、review app 側で必要なのは単なる sample FITS だけではなく、Butler クエリが成立する最小 repository 一式である。
この repo では shared fixture 側でこの一式をすでに生成しているため、review app 側は同じ path を mount するだけでよい。

### 5. review app 用の設定オーバーライド

review app では本番値をそのまま使わず、専用 override を持つ方がよい。

- `use_vault=false`
- `use_gafaelfawr=false`
- `frontend_app_prefix=/review-apps/<project>/<mr>` のような MR 固有 path
- `generator.replicas=2`
- 小さめの resource requests / limits
- review app 専用の `db_url`
- review app 専用の `s3_tile` / `s3_test_data`
- `data_source=dummy` もしくは `data_source=butler`

`k8s/notes/dev-values.yaml` は、この方向の軽量値を考えるときの出発点として使える。

### 6. smoke check

review app は起動するだけでは不十分で、最低限次を CI か手動確認で見たい。

1. `frontend` の health endpoint が通る
2. sample visit 一覧が API から取れる
3. 1 件 quicklook を生成できる
4. quicklook metadata が `ready` まで進む

## 制約と前提

- shared fixture の再利用は hostPath ベースなので、single-node か同等の共有 path を前提にしている
- review app の `PostgreSQL` と `MinIO` は namespace 内 `emptyDir` なので、Pod 再作成時の中身は再生成される
- production 向けの Helm/Phalanx ではなく、repo 内の `kubectl apply` ベースで完結する構成にしている
