# quicklook.utils.rtree

## 背景
既存の `rtree` サードパーティ実装が安定して動作しないケースが確認されたため、
最小限の依存関係で同等の検索機能を提供する独自モジュールを実装しました。
本モジュールは `src/quicklook/utils/rtree/__init__.py` に配置され、
CCD タイルなどの軸平行矩形に対して高速な交差検索を提供します。

## 実装概要
- 軸に平行な矩形を対象とし、中心座標に基づく二分木（Bounding Volume Hierarchy）を構築します。
- 葉ノードの最大要素数 (`max_leaf_size`) を調整可能で、要素数が閾値以下になるまで再帰的に分割します。
- クエリ矩形との交差判定は木を走査し、必要なノードに対してのみ矩形同士の判定を行うため、
  線形走査と比較して実行時間が大幅に削減されます。
- 入力矩形は `BBox` または `(minx, miny, maxx, maxy)` 形式のシーケンスを受け付けます。

## パブリック API
`RectangleIndex` クラスがエントリーポイントです。

| メソッド | 説明 |
| --- | --- |
| `RectangleIndex(max_leaf_size: int = 16)` | インデックスを初期化します。葉ノードの最大要素数を指定できます。 |
| `insert(identifier: int, bounds: BoundsLike)` | 単一の矩形を登録します。識別子は任意の整数で、探索結果として返されます。 |
| `bulk_load(items: Iterable[tuple[int, BoundsLike]])` | 複数の矩形をまとめて登録します。内部では `insert` と同じ検証を実施します。 |
| `intersection(bounds: BoundsLike) -> Iterator[int]` | 指定した矩形と交差する識別子を列挙します。 |

矩形の交差定義は閉区間による重なりで、境界が一致する場合も交差とみなします。

## 使い方の例
```python
from quicklook.utils.rtree import RectangleIndex

index = RectangleIndex()
index.bulk_load([
    (0, (0.0, 0.0, 10.0, 10.0)),
    (1, (5.0, 5.0, 15.0, 15.0)),
])

hits = list(index.intersection((8.0, 8.0, 12.0, 12.0)))
# => [1]
```

`TileInfo` ではこのインデックスを利用して CCD 情報の検索を行っています。
`rtree_index()` 関数から `RectangleIndex` のインスタンスが取得でき、これまでと同じ呼び出し方法で利用可能です。

## 注意点
- インデックスは遅延構築されます。`insert`／`bulk_load` のあと最初にクエリが実行されたタイミングで木が生成されます。
- `BoundsLike` に指定する矩形は `minx <= maxx`、`miny <= maxy` を満たす必要があります。
  これを満たさない場合は `ValueError` となります。
- 既存の `rtree` パッケージは不要になったため、`setup.py` から依存関係を削除しています。
