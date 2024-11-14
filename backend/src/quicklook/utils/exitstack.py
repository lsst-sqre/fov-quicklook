import contextlib


@contextlib.contextmanager
def exit_stack():
    s = contextlib.ExitStack()
    try:
        yield s
    except:  # pragma: no cover
        s.close()
        raise
