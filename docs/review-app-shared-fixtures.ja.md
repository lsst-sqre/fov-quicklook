# review app 用 shared fixtures

`ci/review-app/prepare-shared-fixtures.sh` は、CI を跨いで再利用できる review app 用 fixture を生成する。

この fixture には次が含まれる。

- `dummy` datasource 向けの少量 synthetic `raw` FITS sample data
- `dummy` datasource 用の manifest
- review app 向けの大きめな Butler catalog
- `data-repos.yaml`
- `dummy` / `butler` 切り替え用 env file

## 何を作るか

既定では次を生成する。

- `dummy` 用には 3 visit / 2 CCD (`R01_S00`, `R01_S01`) の軽量 sample
- `butler` 用には約 2000 exposure の catalog
- Butler catalog は画面中央の 9 CCD (`R22_S00..S22`) だけを持ち、filter / program / reason / target / observation type を循環させる
- review app で `DataSource.get_data_sync()` が呼ばれた時点で、添付 JPEG のチャネル画像を `180` 度回転し、中央 3x3 CCD 領域へ bilinear で引き伸ばした仮想 raw FITS をオンザフライ生成する

visit ID は `910001` から始まる固定値で、毎回同じ version なら同じ fixture root を再利用する。

## 出力構成

`REVIEW_APP_SHARED_FIXTURE_ROOT` 配下に次を作る。

```text
<root>/
  VERSION
  fixture-info.json
  dummy.env
  butler.env
  dummy-s3/
    raw/<visit>/<ccd>.fits
    _fixtures/review-app/sample-manifest.json
    _fixtures/review-app/version.txt
  butler/
    data-repos.yaml
    repo/
      butler.yaml
      ...
```

review app deploy では `--butler-registry-url` を渡すため、`butler.yaml` は namespace 内 PostgreSQL の `butler_registry` DB を指す。ローカルで `prepare-shared-fixtures.sh` を単独実行した場合は、既定で SQLite-backed repo になる。

## 使い方

### 1. shared fixture をローカル persistent root に生成

```bash
ci/review-app/prepare-shared-fixtures.sh \
  --root /var/tmp/fov-quicklook-review-app-fixtures
```

同じ version の fixture がすでに存在する場合は再生成せず、そのまま再利用する。

review app 向けの visit 件数を変えたい場合は、次を使える。

```bash
ci/review-app/prepare-shared-fixtures.sh \
  --root /var/tmp/fov-quicklook-review-app-fixtures \
  --visit-count 3 \
  --butler-visit-count 2000
```

### 2. current CI job の `s3_test_data` bucket にも流し込む

`dummy` datasource で使う場合は、review app が参照する `s3_test_data` bucket に sample を同期する。

```bash
export QUICKLOOK_s3_test_data__endpoint=...
export QUICKLOOK_s3_test_data__access_key=...
export QUICKLOOK_s3_test_data__secret_key=...
export QUICKLOOK_s3_test_data__bucket=...
export QUICKLOOK_s3_test_data__secure=false

ci/review-app/prepare-shared-fixtures.sh \
  --root /var/tmp/fov-quicklook-review-app-fixtures \
  --seed-s3
```

`--seed-s3` は `dummy-s3/` 配下を現在の `QUICKLOOK_s3_test_data` 設定先に同期する。
bucket 側の version marker が一致していれば再 upload はスキップする。

## app 側での使い方

### `dummy` datasource

`dummy.env` は最低限次を含む。

- `QUICKLOOK_data_source=dummy`

`dummy` datasource は `s3_test_data` bucket 上の
`_fixtures/review-app/sample-manifest.json` を自動で読み、生成済み visit を表示する。

### `butler` datasource

`butler.env` は次を含む。

- `DAF_BUTLER_REPOSITORY_INDEX=<root>/butler/data-repos.yaml`
- `QUICKLOOK_data_source=butler`
- `QUICKLOOK_ccd_data_types=[...]`

この env file を読み込むと、`reviewapp-ci` という repository 名で local shared fixture の Butler repo を参照できる。
review app deploy では seed job が PostgreSQL 上の `butler_registry` を毎回初期化して metadata を流し込み、実際の raw FITS は `get_data_sync()` 時に仮想生成する。

## 実装メモ

- Butler repo は Python から `lsst.daf.butler` を使って生成する
- `raw` dataset は `LSSTCam/raw/all` collection に紐付ける
- `dummy` 用の synthetic FITS と `butler` 用の virtual FITS は同じ描画ロジックを共有する
- virtual FITS は review app 添付画像の RGB channel を filter ごとに使い分け、`180` 度回転後に中央 3x3 CCD bbox に対して bilinear で補間した領域へ reusable noise を重ねて返す
