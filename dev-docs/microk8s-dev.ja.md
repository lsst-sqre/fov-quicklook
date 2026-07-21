# microk8s 上の pod 開発ワークフロー

この経路は **CI を通さずに**、microk8s に届くマシンから手動で開発用 namespace を作るためのものです。  
pod 自体は **`sleep infinity` で待機** し、dev server の起動は `run.sh start` が pod 内 tmux session に流し込みます。

## 何が作られるか

- namespace: `fov-quicklook-dev`
- `postgres`, `minio`
- `backend-dev` pod
  - `/workspace/fov-quicklook` に現在の checkout を `hostPath` mount
  - Python 実行環境、`uvicorn`、`kubectl`、`tmux`、`fish`、`git` などを同梱
  - `tmux a` で coordinator / generator / frontend API の画面に入れる
- `frontend-dev` pod
  - 同じ source tree を `hostPath` mount
  - Node.js / npm / Vite / `fish` を同梱
  - `tmux a` で Vite dev server の画面に入れる

## 前提

1. **microk8s node 上の checkout から実行すること。** `hostPath` は node の実ファイルパスを mount するため、別マシン上の checkout は見えません。
2. `sudo microk8s ctr` が使えること。dev image は registry に push せず、node の containerd に直接 import します。
3. submodule が必要なら先に初期化しておくこと。

```bash
git submodule update --init --recursive
```

## デプロイ

初回は image build/import、deploy、tmux session の起動までまとめて実行します。

```bash
sh dev/microk8s-dev/run.sh all
```

起動だけやり直したいとき:

```bash
sh dev/microk8s-dev/run.sh start
```

状態確認:

```bash
sh dev/microk8s-dev/run.sh status
```

## 画面に入る

backend:

```bash
kubectl -n fov-quicklook-dev exec -it deploy/backend-dev -- tmux a
```

frontend:

```bash
kubectl -n fov-quicklook-dev exec -it deploy/frontend-dev -- tmux a
```

backend pod の tmux は 3 window です。

- `coordinator`
- `frontend-api`
- `generator`

frontend pod の tmux は 1 window で、必要なら first run で `npm ci` と local package build を先に流します。

Python 側は `--reload` を付けていません。backend の変更を反映したいときは tmux 上で該当プロセスを止めて再実行するか、`run.sh start` をもう一度叩きます。

## アクセス

Vite dev server は port-forward で見るのが一番雑味が少ないです。

```bash
kubectl -n fov-quicklook-dev port-forward svc/frontend-dev 5173:5173
```

ブラウザ:

```text
http://127.0.0.1:5173/fov-quicklook-dev/
```

この URL 配下の `/api/*` は frontend pod から backend service (`backend-dev:9500`) へ proxy されます。

## 動作確認

backend を起動したあと:

```bash
kubectl -n fov-quicklook-dev port-forward svc/backend-dev 9500:9500
curl -fsS http://127.0.0.1:9500/fov-quicklook-dev/api/healthz
```

frontend を起動したあと:

```bash
curl -fsS http://127.0.0.1:5173/fov-quicklook-dev/api/healthz
```

dummy datasource 用の fixture と DB bootstrap は `run.sh deploy` が先に済ませるので、起動後すぐに UI から触れます。

## 片付け

```bash
sh dev/microk8s-dev/run.sh stop
```

## 変えるならここだけ

環境変数で最低限だけ差し替えられます。

| 変数 | 用途 |
|---|---|
| `FQ_DEV_NAMESPACE` | namespace 名 |
| `FQ_DEV_SOURCE_ROOT` | mount する checkout の絶対パス |
| `FQ_DEV_IMAGE` | 使う image を丸ごと上書き |
| `FQ_DEV_BASE_PATH` | Vite / backend の共通 path prefix |
