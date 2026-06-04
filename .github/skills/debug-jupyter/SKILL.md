---
name: debug-jupyter
description: >
  usdf-rsp-dev の `/fov-quicklook/debug/` Jupyter 環境で、
  Butler 調査や任意の Python / bash 実行を再利用可能な形で行うときに使う。
  app token の取得、Jupyter kernel API 経由の実行、Butler 検証の基本手順を含む。
---

# debug Jupyter 実行スキル

## 概要

`https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/debug/` には、
fov-quicklook の deploy target と同じ Butler access 用 env / volume mount を持つ
Jupyter 環境がデプロイされる。

- ingress 認証は `gafaelfawr` cookie で行う
- Phalanx の `applications/fov-quicklook/templates/debug.yaml` では
  `jupyter/base-notebook:latest` を `{{ .Values.config.pathPrefix }}/debug` で公開している
- `values-usdfdev.yaml` では `debug.jupyter: true` が有効
- image 自体は app image ではないので、`lsst-daf-butler` などの Python package は
  notebook セッション側で install する前提で扱う

## 使い分け

- デプロイ / restart / logs / branch 切替は `argocd-deployment`
- app の healthz / frontend / quicklook 再生成確認は `deploy-verification`
- debug Pod 内で Butler の振る舞いや環境差異を調べたいときはこの skill

## 標準の token 取得

broker を使えるなら app token を優先する。

```bash
export BROKER_URL="$(cat ~/.fov-quicklook2/broker-url)"
export BROKER_TOKEN="$(cat ~/.fov-quicklook2/broker-token)"
export GAFAELFAWR_TOKEN="$(
  cd dev/deploy-broker &&
  uv run deploy-broker-client --server "$BROKER_URL" --api-token "$BROKER_TOKEN" get-app-token |
  python -c 'import json,sys; print(json.load(sys.stdin)["token"])'
)"
```

fallback として `dev/.gafaelfawr-token` も使える。

## 任意の Python / bash 実行

repo には `dev/debug-jupyter.sh` を追加してある。
これは Jupyter kernel API に接続し、1 回ごとに一時 kernel を作成して実行し、最後に破棄する。

### Python code を直接流す

```bash
./dev/debug-jupyter.sh --broker python --code 'print("hello from debug")'
```

### Python file を実行する

```bash
./dev/debug-jupyter.sh --broker python --file ./copilot/check-butler.py
```

### bash script を直接流す

```bash
./dev/debug-jupyter.sh --broker bash --code 'python --version && env | grep ^PG'
```

### bash file を実行する

```bash
./dev/debug-jupyter.sh --broker bash --file ./copilot/check-env.sh
```

`--broker` は `~/.fov-quicklook2/broker-url` と `~/.fov-quicklook2/broker-token`
を読み、broker API (`/v1/tokens/app`) から app token を取得する。
token を更新したい場合は `--refresh-broker-token` を付ける。

## Butler の初期化

debug Pod は `jupyter/base-notebook` なので、初回セッションでは Butler 関連 package を
install してから使う前提で進める。

```bash
./dev/debug-jupyter.sh --broker bash --code \
  'python -m pip install --quiet lsst-daf-butler boto3 psycopg2-binary'
```

`PGPASSFILE` は secret mount の権限の都合で、そのままでは Butler が拒否することがある。
一時ファイルへコピーし、owner read-only にしてから使う。

```python
import os
import shutil
import stat
import tempfile


def chown_pgpassfile() -> None:
    if pgfile := os.environ.get("PGPASSFILE"):
        fd, temp_path = tempfile.mkstemp(prefix=".pgpass_")
        os.close(fd)
        shutil.copyfile(pgfile, temp_path)
        os.chmod(temp_path, stat.S_IRUSR)
        os.environ["PGPASSFILE"] = temp_path


chown_pgpassfile()
```

## raw / post_isr_image の基本確認

### raw

```bash
./dev/debug-jupyter.sh --broker python --code '
import os
import shutil
import stat
import tempfile

def chown_pgpassfile() -> None:
    if pgfile := os.environ.get("PGPASSFILE"):
        fd, temp_path = tempfile.mkstemp(prefix=".pgpass_")
        os.close(fd)
        shutil.copyfile(pgfile, temp_path)
        os.chmod(temp_path, stat.S_IRUSR)
        os.environ["PGPASSFILE"] = temp_path

chown_pgpassfile()

from lsst.daf.butler import Butler

default_instrument = "LSSTCam"
butler = Butler(
    "s3://embargo@rubin-summit-users/butler.yaml",
    instrument=default_instrument,
    collections=f"{default_instrument}/raw/all",
)
refs = butler.query_datasets(
    "raw",
    where="detector=0",
    limit=5,
    order_by=["-day_obs", "-exposure"],
)
print([ref.dataId["exposure"] for ref in refs])
'
```

### `post_isr_image`

```bash
./dev/debug-jupyter.sh --broker python --code '
import os
import shutil
import stat
import tempfile

def chown_pgpassfile() -> None:
    if pgfile := os.environ.get("PGPASSFILE"):
        fd, temp_path = tempfile.mkstemp(prefix=".pgpass_")
        os.close(fd)
        shutil.copyfile(pgfile, temp_path)
        os.chmod(temp_path, stat.S_IRUSR)
        os.environ["PGPASSFILE"] = temp_path

chown_pgpassfile()

from lsst.daf.butler import Butler

butler = Butler(
    "s3://embargo@rubin-summit-users/butler.yaml",
    collections=["LSSTCam/runs/nightlyValidation"],
)
refs = butler.query_datasets(
    "post_isr_image",
    where="detector=0",
    limit=5,
    order_by=["-day_obs", "-exposure"],
)
print([ref.dataId["exposure"] for ref in refs])
'
```

## 調査フローの定型

1. broker から app token を取る (`--broker`)
2. 必要なら Butler package を install
3. `PGPASSFILE` を一時ファイルへ退避して権限を整える
4. まず `print(os.environ["PGPASSFILE"])` や `python --version` など最小実行で疎通確認
5. その後に Butler query を流し、必要なら script file 化して再利用する

## 注意点

- token 切れや `302` が出る場合は `--refresh-broker-token` で app token を取り直す
- 実行ごとに ephemeral kernel を作るので、状態は持ち越さない
- bash は Python kernel 内で一時 `.sh` を書いて `bash` 実行している
- debug Pod に repo checkout は無いので、file 実行は **local file の内容を送って remote で実行**
- Butler query の結果が `MissingCollectionError` なら collection / repository の指定違いを疑う
