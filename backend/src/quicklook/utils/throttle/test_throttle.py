import time
import pytest
from quicklook.utils.throttle import throttle, flush

# pytestmark = pytest.mark.focus


def test_throttle():
    calls = []

    @throttle(0.05)
    def test_func(x):
        calls.append(x)

    test_func(1)
    test_func(2)
    assert calls == [1]

    time.sleep(0.1)
    test_func(3)
    test_func(4)
    assert calls == [1, 3]
    flush(test_func)
    assert calls == [1, 3, 4]
    flush(test_func)
    assert calls == [1, 3, 4]
