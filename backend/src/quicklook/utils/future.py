from concurrent.futures import Future


def _check_error(f: Future):
    error = f.exception()
    if error:  # pragma: no cover
        raise error


def check_future_error(f: Future):
    f.add_done_callback(_check_error)
    return f
