# exclude_cached_properties_from_pickle

`exclude_cached_properties_from_pickle` は、クラスデコレータで、`functools.cached_property` で定義されたプロパティを pickle (シリアライズ) の際に除外するためのユーティリティです。

このデコレータは、クラスに `__getstate__` と `__setstate__` を追加（上書き）します。`__getstate__` はインスタンス辞書 (`__dict__`) から `cached_property` に対応する属性名を取り除き、キャッシュ化された値をシリアライズしないようにします。`__setstate__` は復元時に通常の辞書更新を行います（元の `__getstate__`/`__setstate__` が定義されていればそれを尊重します）。

主な利点:
- キャッシュ化された大きなオブジェクトを pickle に含めないことで、ファイルサイズとメモリ使用を削減できます。
- 再ロード時にプロパティは遅延評価され、必要になったときに再計算されます。

使い方:

```python
from quicklook.utils.exclude_cached_properties_from_pickle import exclude_cached_properties_from_pickle
from functools import cached_property

@exclude_cached_properties_from_pickle
class Foo:
    def __init__(self):
        self.x = 1

    @cached_property
    def heavy(self):
        # 高コスト計算を行い結果をキャッシュ
        return [0] * 10_000_000

# これで pickle 時に `heavy` のキャッシュは含まれません
```

注意点:
- `cached_property` 以外で明示的に `__dict__` にキャッシュを書き込む実装（例えば `self.heavy = ...`）があると、その値は pickle に含まれます。デコレータは `cached_property` インスタンスを検出して名前を除去するだけです。
