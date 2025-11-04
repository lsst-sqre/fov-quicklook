# Timer

Python's standard `threading.Timer` creates a new thread each time a new timer is set.
Running many timers simultaneously creates too many threads, so we implement a mechanism to manage multiple timers with a single thread.

## Implementation

* One thread manages multiple timers.
* The management thread is created at the first call.
* This management thread checks registered timers once per second and executes timers when their time arrives.
* Check interval is configurable

## Usage

Provides an interface compatible with Python's `threading.Timer`, but you need to call `start()` to register the timer.

```python
from quicklook.utils.timer import Timer

timer = Timer(30, print, args=("hello",))
timer.start()

# Cancel if you want to before execution
timer.cancel()
```

Registered timers can be canceled with `cancel()`. Check completion with the `finished` property and check if waiting to execute with `is_alive()`.

## API

### Timer

```
Timer(interval: float, function: Callable[..., Any], args: tuple[Any, ...] | None = None,
	kwargs: dict[str, Any] | None = None)
```

* `function(*args, **kwargs)` is executed once after `interval` seconds.
* `start()` can only be called once. Second and subsequent calls raise `RuntimeError`.
* `cancel()` cancels the execution if called before execution.
* `is_alive()` returns whether the timer is waiting to execute.
* `finished` is a read-only property that returns whether execution is complete (or canceled).

### Changing Check Interval

The interval at which the management thread checks timers is 1.0 second by default. Change with `set_check_interval()`.

```python
from quicklook.utils.timer import set_check_interval

set_check_interval(0.05)
```

The setting is shared across the entire process and immediately reflected in already-running management threads. Useful when handling many timers in a short time, such as in tests.
