import inspect
from functools import cached_property


def exclude_cached_properties_from_pickle(cls):
    original_getstate = getattr(cls, '__getstate__', None)
    original_setstate = getattr(cls, '__setstate__', None)

    def __getstate__(self):
        # 既存の __getstate__ があればそれを使う
        state = (original_getstate(self) if original_getstate else self.__dict__).copy()
        for name, attr in inspect.getmembers(type(self)):
            if isinstance(attr, cached_property):
                state.pop(name, None)
        return state

    def __setstate__(self, state):
        if original_setstate:
            original_setstate(self, state)
        else:
            self.__dict__.update(state)

    cls.__getstate__ = __getstate__
    cls.__setstate__ = __setstate__
    return cls