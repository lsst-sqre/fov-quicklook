# Butler と Data Query の仕組み

このページは、FOV-Quicklook の `Data Query` が Butler をどう使っているかをまとめたメモです。特に次の疑問に答えることを目的にしています。

- `Data Query` は内部で何をしているのか
- Butler のどの機能を使っているのか
- `data_type=raw` は CCD 単位の検索なのか、exposure 単位の検索なのか
- Butler の registry ではどんな種類のテーブルが重要なのか

## まず結論

- FOV-Quicklook の `Data Query` は、一覧表示では **CCD 単位ではなく exposure/visit 単位** で検索しています。
- ただし `raw` データセットそのものは Butler 上では **detector (CCD) を含む dataset** です。
- 現在の実装では `raw` の一覧を出すときに `exposure` dimension を引き、その exposure を開いたあとに detector ごとの `raw` dataset を列挙しています。
- したがって、**「一覧検索は exposure 単位、実データ取得は CCD 単位」** という理解がいちばん近いです。
- `data_type=raw` で **exposure 単位の検索は可能** です。むしろ現状の `Data Query` API/UI はそれを前提にしています。
- 一方で、**特定 CCD を条件にした検索** は現在の `Data Query` API にはありません。
- カレンダーは **1 日ごとに 30 回クエリするのではなく、月ごとに 1 回** `day_counts` API を呼びます。
- ただし月次 API は「月内のすべての `day_obs + data_id_dimension`」を 1 回で取得してから、日別件数に集計しています。
- `by_uuid` は **repository + UUID** があれば Butler 上の dataset を特定でき、その `datasetType.name` から `data_type` も引けます。
- ただし `by_uuid` をそのまま画面表示やデータ取得につなげるには、**解決後の dataset type に対応する `ccd_data_types` 設定**が必要です。
- 一覧検索の query string でユーザーが指定できるのは現状 `limit` までで、`order` は設定固定、`offset` は未対応です。

## Data Query のリクエストの流れ

`Data Query` 画面では、`/query?` の後ろにそのままクエリ文字列を入れます。たとえば:

```text
data_type=raw&repository_name=embargo&day_obs=20260128&limit=20
```

流れは次のとおりです。

1. フロントエンドの `frontend/app/src/pages/QueryPage/index.tsx` が URL の query string を読む
2. `frontend/app/src/pages/QueryPage/queryParams.ts` が `data_type` / `repository_name` / `day_obs` / `exposure` / `limit` をパースする
3. `frontend/app/src/store/api/openapi.ts` の `listVisits` が `GET /api/visits` を呼ぶ
4. `backend/src/quicklook/frontend/api/visits.py` が `Query` オブジェクトを作り、data source に渡す
5. Butler 使用時は `backend/src/quicklook/datasource/butler_datasource/__init__.py` の `ButlerDataSource.query_visits_sync` が処理する
6. 最終的に `DataTypeSpecificDataSource.query_visits` が Butler の query API を実行する

一覧検索で中心になっているのは次の呼び出しです。

```python
self._query_dimension_records(
    self.data_id_dimension,
    datasets=self.butler_data_type,
    where=where,
    limit=q.limit,
    order_by=self.order_by,
)
```

ここで重要なのは、**どの dimension を一覧の単位にするかは `data_id_dimension` で決まる** ことです。

## FOV-Quicklook が Butler の何を使っているか

FOV-Quicklook は Butler を「dataset を 1 件ずつ取るだけの道具」としてではなく、**registry を検索するインデックス**としてかなり使っています。

| Butler 機能 | FOV-Quicklook での用途 |
| --- | --- |
| `Butler(repository_name, instrument=..., collections=...)` | 対象 repository と collection の固定 |
| `registry.queryDimensionRecords(...)` | exposure/visit 一覧の生成 |
| `registry.queryDataIds(...)` | 日ごとの件数集計 (`/api/visits/day_counts`) |
| `query_datasets(...)` / `registry.queryDatasets(...)` | dataset ref の取得、CCD 列挙、UUID 代表値の取得 |
| `registry.getDataset(UUID(...))` | `by_uuid` 形式の visit 解決 |
| `getURI(...)` | 実ファイルの URI 解決 |

### 1. Butler の初期化

各 data type ごとに次のように Butler を作っています。

```python
Butler(
    data_type_config.repository_name,
    instrument=data_type_config.instrument,
    collections=data_type_config.collections,
)
```

ここで `collections` が固定されるので、`Data Query` は「repository 内の全 dataset」を自由検索しているのではなく、**設定済み collection の範囲だけ**を見ます。

### 2. 一覧検索

一覧は `queryDimensionRecords` ベースです。

- `raw`, `post_isr_image`: `data_id_dimension='exposure'`
- `difference_image`, `preliminary_visit_image`: `data_id_dimension='visit'`

つまり、同じ `Data Query` UI でも data type によって一覧の粒度が変わります。

### 3. 日別件数

カレンダー用の日別件数は `queryDataIds(['day_obs', self.data_id_dimension], ...)` で数えています。ここでも「数える単位」は `data_id_dimension` に従います。

## カレンダーの仕組み

カレンダーは Home 画面左側の検索欄にある日付選択 UI です。フロントエンドでは `frontend/app/src/pages/Home/VisitList/index.tsx` の `SearchBox` が担当しています。

### フロントエンド側の挙動

- カレンダーを開くと `useListVisitDayCountsQuery({ dataType, repositoryName, calendarMonth })` が動く
- これは `calendarOpen` が `true` のときだけ実行される
- 月送り (`Prev` / `Next`) をすると `calendarMonth` が変わり、その月について再取得する

つまり、**日ごとに 30 回 API を叩くのではなく、「表示中の月につき 1 回」**です。

月を切り替えた場合は、その新しい月についてもう 1 回呼ばれます。

### バックエンド側の挙動

`/api/visits/day_counts` は最終的に次の処理を行います。

```python
data_ids = self._query_data_ids(
    ['day_obs', self.data_id_dimension],
    datasets=self.butler_data_type,
    where=f"day_obs>={start_day_obs} and day_obs<{end_day_obs}",
    order_by=['day_obs'],
)
counts_by_day_obs = Counter(int(data_id['day_obs']) for data_id in data_ids)
```

重要なのは次の点です。

- **1 回の Butler query** で月内の対象 data ID をまとめて取る
- 返しているのは `queryDimensionRecords('exposure')` のような完全な record 一覧ではなく、`day_obs` と `data_id_dimension` を含む data ID 列
- 日別件数の集計自体はアプリ側 (`Counter`) で行っている

したがって、質問に対しては次の答えになります。

- **日毎に 30 回クエリしているわけではない**
- **月内エントリーをまとめて 1 回で取得してから集計している**

より正確には、「月内の全 record を丸ごと取る」というより、**月内の `day_obs + exposure/visit` の組を 1 回で取って件数化している**、という実装です。

## Butler registry と backend 側 PostgreSQL table の対応

`Data Query` 周りでは public API だけでなく、Butler registry がぶら下げている private な SQL manager も一部使っています。コード上の入口は `backend/src/quicklook/datasource/butler_datasource/__init__.py` の `_get_sql_registry()` / `_get_db_connection()` です。

| 用途 | Butler 側の入口 | PostgreSQL table | 備考 |
| --- | --- | --- | --- |
| collection 一覧 / 存在確認 | `sql_registry._managers.collections._tables.collection` | `collection` | `name` と `collection_id` を使う |
| dataset type 一覧 / 存在確認 | `sql_registry._managers.datasets._static.dataset_type` | `dataset_type` | `tag_association_table` から dataset type ごとの dynamic table 名が分かる |
| 月次 `day_counts` の高速経路 | `sql_registry._managers.datasets._find_storage(dataset_type).dynamic_tables` と `sql_registry._managers.dimensions._tables[exposure|visit]` | `dataset_tags_*` + `exposure` / `visit` | `collection_id` で絞って `day_obs` ごとに `COUNT(DISTINCT exposure|visit)` する |
| `by_uuid` 解決 | `registry.getDataset(UUID(...))` | （内部的には `dataset` / `dataset_type` / `run` 由来） | 実装は public API を優先し、table を直読みしない |

### `day_counts` の SQL 経路

現在の backend は、collection が固定されている通常ケースではまず SQL 経路を試します。流れは次のとおりです。

1. `collection.name -> collection.collection_id` を 1 回だけ引く
2. dataset type から対応する `dataset_tags_*` table を得る
3. `dataset_tags_*` と `exposure` または `visit` table を `instrument + exposure/visit id` で join する
4. `day_obs >= ... and day_obs < ...` で月を絞り、`COUNT(DISTINCT exposure|visit)` を `GROUP BY day_obs` する

これは `collection` table との join を毎回 hot path に入れないためで、debug-jupyter での実測でも `queryDataIds(...)+Counter` より速いケースがありました。Butler の private SQL internals が使えない環境では、従来どおり public API の `queryDataIds()` に自動で戻します。

### 4. 実データ参照

一覧から exposure/visit を選んだ後は、`query_datasets(...)` で dataset ref を引いて detector ごとに整理し、`getURI(...)` から実ファイルを取得します。

`raw` の場合、ここで初めて CCD 単位の dataset 群を扱います。

## `data_type=raw` は CCD 単位でしか検索できないのか

**いいえ。現状の `Data Query` は `raw` を exposure 単位で検索しています。**

`backend/src/quicklook/config/__init__.py` のデフォルト設定では `raw` はこうなっています。

```python
CcdDataTypeConfig(
    data_type='raw',
    display_name='Raw',
    collections=['LSSTCam/raw/all'],
    data_id_dimension='exposure',
    order_by=['-day_obs', '-exposure'],
    partial=False,
    repository_name='embargo',
    instrument='LSSTCam',
)
```

このため `query_visits` は `queryDimensionRecords('exposure', datasets='raw', ...)` を実行します。返ってくる一覧行は detector ごとの row ではなく、**raw dataset が存在する exposure の row** です。

### では CCD 単位なのはどこか

`raw` dataset 自体の data ID には detector が入るため、実データ取得時は CCD 単位です。

たとえば以下の処理は `exposure=<id>` で dataset refs を引き、その中から detector ごとに 1 件ずつ扱っています。

- `list_ccds`
- `_refs_by_visit`
- `get_metadata`
- `get_data`

つまり:

- **検索結果の一覧**: exposure 単位
- **実際の FITS / metadata / tile 取得**: CCD 単位

です。

### CCD を条件にして検索できるか

**現状の `Data Query` API/UI ではできません。**

`/api/visits` が受け付けるのは現在:

- `data_type`
- `repository_name`
- `day_obs`
- `exposure`
- `limit`

だけで、`detector` や `ccd_name` をクエリ条件として渡す口はありません。

そのため、**「R22_S11 の raw だけを一覧したい」** のような検索は今の `Data Query` には未実装です。

## exposure 単位での検索はできるのか

**できます。**

`/api/visits` は `exposure` パラメータを受け付けます。`raw` の場合は `data_id_dimension='exposure'` なので、たとえば:

```text
data_type=raw&repository_name=embargo&exposure=2026012800342
```

のような query string で exposure を直接絞れます。

補足:

- `day_obs` を省略した場合、バックエンドは最新の `day_obs` を自動補完します
- Home 画面の通常検索は日付入力中心ですが、`Data Query` 画面では query string を直接書けるので exposure 指定が可能です

## ページネーションできるか

**現状は「件数制限つきの先頭 N 件取得」で、一般的なページネーション API にはなっていません。**

### `limit`

`limit` は指定できます。

- `frontend/app/src/pages/QueryPage/queryParams.ts` が `limit` を受け取る
- `backend/src/quicklook/frontend/api/visits.py` が `/api/visits?limit=...` を受け取る
- backend の `Query` dataclass にも `limit` フィールドがある
- Butler query では `records.limit(limit)` を使って反映している

したがって、**「最大何件返すか」** は今でも指定可能です。

### `order`

**ユーザーから自由には指定できません。**

現在の並び順は `ccd_data_types` 設定の `order_by` に固定されています。例:

- `raw`: `['-day_obs', '-exposure']`
- `difference_image`: `['-visit']`

実装では `self.order_by` をそのまま Butler query result に適用しています。

```python
records = self._butler.registry.queryDimensionRecords(dimension, **kwargs)
records = records.order_by(*order_by)
records = records.limit(limit)
```

そのため、**「limit は可変、order は data type ごとの設定固定」** という状態です。

### `offset`

**現状の FOV-Quicklook API/UI では指定できません。**

少なくとも今の実装には:

- `/api/visits` の `offset` パラメータ
- `Query` dataclass の `offset`
- frontend の query string パーサでの `offset`
- Butler 呼び出し側での `offset` 適用

のどれもありません。

また、このコードパスで使っている Butler query interface でも、現状コード上は `order_by(...).limit(...)` までしか使っていません。

### つまり何ができて、何ができないか

| 項目 | 現状 |
| --- | --- |
| `limit` | できる |
| `order` を query string で指定 | できない |
| `offset` を query string で指定 | できない |
| 典型的な `limit + offset` ページネーション | 未実装 |

### 実装するとしたら

将来的にページネーションを入れるなら、少なくとも:

1. `/api/visits` に `offset` あるいは cursor を足す
2. frontend の `QueryPage` にも対応する
3. data type ごとに安定した sort order を保証する

が必要です。

特に `offset` 方式にするなら、**並び順が固定で安定していること** が前提になります。今の実装は order 自体は固定ですが、API 契約として pagination を保証しているわけではないので、その整理が必要です。

## Butler の関連テーブルをどう理解するとよいか

Butler は「1 枚の巨大テーブル」ではなく、**dimension と dataset registry を中心にした複数テーブル構造**になっています。

FOV-Quicklook を理解するうえでは、物理 SQL の細かい差分よりも、次の分類で把握すると分かりやすいです。

### 1. Dimension tables

代表例:

- `exposure`
- `visit`
- `detector`
- `instrument`
- `physical_filter`

これらは「天文学的な概念」を表す表です。`queryDimensionRecords('exposure', ...)` のような呼び出しは、概念的にはこの層を読んでいます。

FOV-Quicklook の `Data Query` 一覧は、主にこの層を読んでいます。

### 2. Dataset type 定義

代表例:

- `raw`
- `post_isr_image`
- `difference_image`
- `preliminary_visit_image`

dataset type には「どの dimensions を key に持つ dataset か」が定義されています。FOV-Quicklook 側では `CcdDataTypeConfig.data_type` に対応します。

### 3. Collections

代表例:

- `LSSTCam/raw/all`
- `LSSTCam/runs/nightlyValidation`

Butler の dataset は collection と組み合わせて解決されます。FOV-Quicklook は UI ごとに collection を自由入力させるのではなく、`ccd_data_types` 設定で collection を固定しています。

### 4. Dataset / association 系

この層は概念的には次を管理します。

- dataset UUID
- dataset type
- data ID
- run collection との関係
- tagged/calibration collection との関係

`query_datasets(...)` で返る `DatasetRef` は、この層を経由して「その exposure/visit に属する実 dataset」を指します。

`by_uuid` 形式の visit 解決で使っている `registry.getDataset(UUID(...))` もこの層です。

## `by_uuid` と `ccd_data_types` / Phalanx 設定の関係

`by_uuid` は独立した dataset type を `ccd_data_types` に足しているわけではありません。実装上は:

1. `embargo:by_uuid:<uuid>` のような visit name を受け取る
2. `registry.getDataset(UUID(...))` で Butler から実 dataset を引く
3. その dataset の `datasetType.name` を調べる
4. `_get_datasource(dataset_type, repository_name)` で **対応する data source 設定**を探す

という流れです。

このため、**`by_uuid` のために必要なのは `by_uuid` 設定ではなく、「解決先 dataset type の `ccd_data_types` 設定」**です。

### repository と UUID があれば `data_type` も分かるか

**はい。現在の実装では分かります。**

`by_uuid` 解決は repository ごとに Butler を開いてから:

1. `registry.getDataset(UUID(...))` で dataset を 1 件引く
2. 返ってきた `DatasetRef.datasetType.name` を読む
3. その `datasetType.name` を FOV-Quicklook 側の `data_type` として使う

という流れです。

```python
repository_butler = _get_repository_butler(visit.repository_name)
dataset_ref = repository_butler.registry.getDataset(UUID(visit.name))
dataset_type = cast(str, dataset_ref.datasetType.name)
```

したがって、**呼び出し側が最初から `data_type` を知っている必要はありません**。`repository_name` と UUID があれば、Butler registry から:

- その UUID がどの dataset か
- その dataset の `datasetType.name`
- `data_id_dimension` に対応する `exposure` / `visit`
- 必要なら `detector`

まで取得できます。

ただし、FOV-Quicklook がその後の処理を続けるには `_get_datasource(dataset_type, repository_name)` が成功する必要があるので、**「特定はできるが、アプリとして扱えるか」は `ccd_data_types` 設定に依存する**、という切り分けです。

### `difference_image` を `ccd_data_types` から削れるか

**`difference_image` を `by_uuid` で開きたいなら削れません。**

理由は、UUID 解決後に `difference_image` 用の datasource を `config.ccd_data_types` から引けないと、ここで失敗するからです。

```python
dataset_type = cast(str, dataset_ref.datasetType.name)
datasource = _get_datasource(dataset_type, visit.repository_name)
```

もし設定がなければ、最終的に次の意味のエラーになります。

- `UUID ... resolves to unsupported dataset type difference_image ...`

したがって、Phalanx の `values.yaml` から `difference_image` を外すと、**少なくとも `difference_image` の `by_uuid` 解決は壊れます**。

### `ccd_data_types` は右上ボタンだけに使われているのか

**いいえ。現状は右上ボタン専用ではありません。**

`ccd_data_types` は少なくとも次に使われています。

| 用途 | 使っている場所 |
| --- | --- |
| 既定の data source 決定 | `frontend/app/src/store/features/homeSlice.ts` |
| 左側の data source 選択プルダウン | `frontend/app/src/pages/Home/VisitList/index.tsx` |
| 右上の data type 切り替えボタン | `frontend/app/src/pages/Home/DataTypeSwitch.tsx` |
| exposure ごとの利用可能 type 判定 | `backend/src/quicklook/datasource/butler_datasource/__init__.py#get_exposure_data_types_sync` |
| `by_uuid` 解決後の datasource 決定 | `backend/src/quicklook/datasource/butler_datasource/__init__.py#_resolve_visit_cache` |

つまり、現在の `ccd_data_types` は:

- UI の表示候補
- backend の lookup 設定
- `by_uuid` の解決先サポート範囲

をまとめて兼ねています。

### 右上ボタンだけに限定できるか

**設計変更すれば可能ですが、現状はそうなっていません。**

たとえば将来的には:

- backend が解決可能な data type 一覧
- 左側 UI に見せる data type 一覧
- 右上ボタンに見せる data type 一覧

を別設定に分けることはできます。

ただし今の実装では `ccd_data_types` がそれらを一括で担っているため、**「`difference_image` は by_uuid のためには残したいが、通常 UI には出したくない」** という要件はそのままでは満たせません。

### 5. Datastore location

registry は dataset の論理情報を持ち、実ファイルの場所は datastore 側にあります。FOV-Quicklook は最後に `getURI(...)` を使って URI を引き、そこから FITS や zip 内ファイルを読んでいます。

そのため、**一覧検索は registry 中心、実データ取得は datastore 中心** と見ると整理しやすいです。

## FOV-Quicklook の data type ごとの一覧単位

現行デフォルト設定では次のようになっています。

| data type | collection | 一覧の単位 (`data_id_dimension`) | 実データの粒度 |
| --- | --- | --- | --- |
| `raw` | `LSSTCam/raw/all` | `exposure` | detector ごとの raw dataset |
| `post_isr_image` | `LSSTCam/runs/nightlyValidation` | `exposure` | detector ごとの processed dataset |
| `difference_image` | `LSSTCam/runs/nightlyValidation` | `visit` | detector ごとの difference image |
| `preliminary_visit_image` | `LSSTCam/runs/nightlyValidation` | `visit` | visit ベース |

## 実装を読むときの入口

- Query UI: `frontend/app/src/pages/QueryPage/index.tsx`
- query string パース: `frontend/app/src/pages/QueryPage/queryParams.ts`
- visits API: `backend/src/quicklook/frontend/api/visits.py`
- Butler data source: `backend/src/quicklook/datasource/butler_datasource/__init__.py`
- data type 設定: `backend/src/quicklook/config/__init__.py`

## 補足

Butler の物理テーブル名や join の詳細は Butler のバージョンや registry backend によって差が出ることがあります。ですが、FOV-Quicklook の説明として重要なのは次の 3 点です。

1. 一覧検索は `queryDimensionRecords` / `queryDataIds` で dimension 側を見ている
2. 実データ参照は `query_datasets` で dataset ref を引いてから行う
3. `raw` は dataset としては CCD 単位だが、現行 UI の一覧検索は exposure 単位である
