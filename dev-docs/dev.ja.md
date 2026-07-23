# microk8s 開発ガイド

このリポジトリの開発は **microk8s 上の dev pod** を前提にする。
`dev/microk8s-dev/run.sh` が、PostgreSQL / MinIO / backend-dev / frontend-dev を作り、
backend と frontend の開発サーバーを pod 内 tmux で起動する。

## クイックスタート

1. **microk8s node 上の checkout で作業する。** `hostPath` mount 前提なので別マシンの checkout は使えない。
2. **submodule を初期化する。**
3. **dev pod を作る。**

```bash
git submodule update --init --recursive
sh dev/microk8s-dev/run.sh all
sh dev/microk8s-dev/run.sh status
```

## 何が作られるか

| 要素 | 役割 |
|---|---|
| `fov-quicklook-dev` namespace | 開発用の隔離環境 |
| `postgres`, `minio` | backend が使う state / object storage |
| `backend-dev` | coordinator / frontend-api / generator を tmux で起動する pod |
| `frontend-dev` | Vite dev server を起動する pod |

どちらの pod も `/workspace/fov-quicklook` に現在の checkout を `hostPath` mount する。

checkout 上のファイル変更は pod 内にも即時で見える。backend は `backend/src/**/*.py` の変更を自動で再読込する。`dev/microk8s-dev/*.sh` や環境変数を変えたときだけ process を再起動する。

## 起動と入り方

初回または Dockerfile / 依存を作り直したいとき:

```bash
sh dev/microk8s-dev/run.sh all
```

既存の dev 環境を捨てて作り直したいとき:

```bash
sh dev/microk8s-dev/run.sh redeploy
```

`redeploy` の `seed-fixtures` / `bootstrap-db` も checkout を `hostPath` mount して実行するので、**source だけの変更なら image 再 build は不要**。

pod はそのままで tmux だけ起動し直したいとき:

```bash
sh dev/microk8s-dev/run.sh start
```

backend を pod の外からまとめて再起動したいとき:

```bash
sh dev/microk8s-dev/run.sh restart-backend
```

backend pod の中から tmux で手動再起動したいとき:

```bash
sh dev/microk8s-dev/backend-restart.sh all
sh dev/microk8s-dev/backend-restart.sh coordinator
sh dev/microk8s-dev/backend-restart.sh frontend-api
sh dev/microk8s-dev/backend-restart.sh generator
```

backend pod:

```bash
kubectl -n fov-quicklook-dev exec -it deploy/backend-dev -- tmux a
```

frontend pod:

```bash
kubectl -n fov-quicklook-dev exec -it deploy/frontend-dev -- tmux a
```

backend 側 tmux は `coordinator` / `frontend-api` / `generator` の 3 window 構成。

## アクセス

```bash
kubectl -n fov-quicklook-dev port-forward svc/frontend-dev 5173:5173
```

ブラウザ:

```text
http://127.0.0.1:5173/fov-quicklook-dev/
```

この path 配下の `/api/*` は frontend pod から backend service (`backend-dev:9500`) に proxy される。

## 動作確認

backend:

```bash
kubectl -n fov-quicklook-dev port-forward svc/backend-dev 9500:9500
curl -fsS http://127.0.0.1:9500/fov-quicklook-dev/api/healthz
```

frontend:

```bash
curl -fsS http://127.0.0.1:5173/fov-quicklook-dev/api/healthz
```

fixture と DB bootstrap は `run.sh deploy` が先に済ませるので、起動直後から UI と API を触れる。

## よく使う周辺作業

- backend のテスト / 型チェック: `/dev-docs/backend.ja.md`
- frontend の build / 型生成 / テスト: `/dev-docs/frontend.ja.md`
- review app CI と shared fixture: `/dev-docs/ci.ja.md`

microk8s 開発は **手で触るための常駐環境**、review app CI は **MR ごとに使い捨てる自動環境** という棲み分け。

## 片付け

```bash
sh dev/microk8s-dev/run.sh stop
```

## 変更しやすい値

| 変数 | 用途 |
|---|---|
| `FQ_DEV_NAMESPACE` | namespace 名 |
| `FQ_DEV_SOURCE_ROOT` | mount する checkout の絶対パス |
| `FQ_DEV_IMAGE` | 使う image を丸ごと上書き |
| `FQ_DEV_BASE_PATH` | Vite / backend の共通 path prefix |
| `FQ_DEV_DUMMY_VISIT_COUNT` | DummyDataSource で作る visit 数（既定 50） |
| `FQ_DEV_BUTLER_VISIT_COUNT` | 併せて作る Butler catalog 件数（既定 0） |
