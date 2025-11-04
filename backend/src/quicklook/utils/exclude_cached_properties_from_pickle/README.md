# exclude_cached_properties_from_pickle

`exclude_cached_properties_from_pickle` is a class decorator utility that excludes properties defined with `functools.cached_property` from pickle (serialization).

This decorator adds (or overwrites) `__getstate__` and `__setstate__` to the class. `__getstate__` removes attribute names corresponding to `cached_property` from the instance dictionary (`__dict__`) to prevent cached values from being serialized. `__setstate__` performs normal dictionary update on restoration (respecting original `__getstate__`/`__setstate__` if defined).

Main benefits:
- Reduces file size and memory usage by not including large cached objects in pickle.
- On reload, properties are lazily evaluated and recomputed when needed.

Usage:

```python
from quicklook.utils.exclude_cached_properties_from_pickle import exclude_cached_properties_from_pickle
from functools import cached_property

@exclude_cached_properties_from_pickle
class Foo:
    def __init__(self):
        self.x = 1

    @cached_property
    def heavy(self):
        # Perform expensive computation and cache the result
        return [0] * 10_000_000

# Now the `heavy` cache is not included during pickling
```

Cautions:
- If there are implementations that explicitly write caches to `__dict__` other than `cached_property` (e.g., `self.heavy = ...`), those values will be included in pickle. The decorator only detects `cached_property` instances and removes their names.
