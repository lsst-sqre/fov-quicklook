import pickle
from functools import cached_property
from dataclasses import dataclass

from quicklook.utils.exclude_cached_properties_from_pickle import (
    exclude_cached_properties_from_pickle,
)


# module-level dict used by C.__getstate__/__setstate__ to record calls
CALLS: dict = {}


@exclude_cached_properties_from_pickle
class A:
    def __init__(self):
        self.value = 123

    @cached_property
    def expensive(self):
        # set a sentinel to prove it was computed
        return object()


@exclude_cached_properties_from_pickle
class B:
    def __init__(self):
        self.x = [1, 2, 3]

    @property
    def normal(self):
        return sum(self.x)


@exclude_cached_properties_from_pickle
class C:
    def __init__(self, calls):
        self.keep = 'keep'
        self.drop = 'drop'
        # don't rely on instance attributes for pickling callbacks; use CALLS dict

    @cached_property
    def cached(self):
        return 999

    def __getstate__(self):
        # only include 'keep'
        CALLS['getstate'] = True
        return {'keep': self.keep}

    def __setstate__(self, state):
        CALLS['setstate'] = True
        self.__dict__.update(state)


def test_cached_property_excluded_from_pickle():
    a = A()
    # compute and cache the property
    sentinel = a.expensive
    assert a.__dict__.get('expensive') is sentinel

    data = pickle.dumps(a)
    b = pickle.loads(data)

    # value should be preserved
    assert b.value == 123

    # cached property should not be present in __dict__ after unpickling
    assert 'expensive' not in b.__dict__

    # accessing the property computes a new object (i.e., not equal to sentinel)
    assert b.expensive is not sentinel


def test_non_cached_attributes_preserved():
    b = B()
    data = pickle.dumps(b)
    c = pickle.loads(data)
    assert c.x == [1, 2, 3]
    assert c.normal == 6


def test_respects_existing_getstate_setstate():
    CALLS.clear()
    c = C(None)
    # compute the cached property to populate cache
    _ = c.cached
    data = pickle.dumps(c)
    d = pickle.loads(data)

    assert CALLS.get('getstate', False) is True
    assert CALLS.get('setstate', False) is True
    assert hasattr(d, 'keep')
    assert not hasattr(d, 'drop')


@exclude_cached_properties_from_pickle
@dataclass
class DDataclass:
    a: int
    b: str = 'default'

    @cached_property
    def computed(self):
        return (self.a, self.b)


def test_dataclass_with_cached_property_serialization():
    d = DDataclass(10, 'x')
    # evaluate cached property
    val = d.computed
    assert d.__dict__.get('computed') is val

    data = pickle.dumps(d)
    e = pickle.loads(data)

    # fields should be preserved
    assert e.a == 10
    assert e.b == 'x'

    # cached property should not be serialized; after unpickle it gets recomputed
    assert 'computed' not in e.__dict__
    assert e.computed == (10, 'x')
