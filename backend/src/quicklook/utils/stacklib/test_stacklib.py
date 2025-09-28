from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable

import pytest

from quicklook.utils import stacklib


class DummyContext(contextlib.AbstractContextManager["DummyContext"]):
    def __init__(self) -> None:
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self) -> DummyContext:
        self.enter_count += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.exit_count += 1
        return False


def test_stack_push_and_cleanup() -> None:
    stack: stacklib.Stack[int] = stacklib.Stack()

    with pytest.raises(IndexError):
        stack()

    with stack.push(1):
        assert stack() == 1
        with stack.push(2):
            assert stack() == 2
        assert stack() == 1

    with pytest.raises(IndexError):
        stack()


def test_stack_push_restores_state_on_exception() -> None:
    stack: stacklib.Stack[str] = stacklib.Stack()

    with pytest.raises(RuntimeError):
        with stack.push("value"):
            raise RuntimeError("boom")

    with pytest.raises(IndexError):
        stack()


def test_thread_local_context_isolated_per_thread() -> None:
    created_contexts: list[DummyContext] = []

    def factory() -> DummyContext:
        ctx = DummyContext()
        created_contexts.append(ctx)
        return ctx

    with stacklib.thread_local_context(factory) as get_ctx:
        main_ctx = get_ctx()
        assert main_ctx is get_ctx()

        worker_contexts: list[DummyContext] = []

        def worker() -> None:
            worker_contexts.append(get_ctx())

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert len(worker_contexts) == 1
        worker_ctx = worker_contexts[0]
        assert worker_ctx is not main_ctx
        assert worker_ctx.enter_count == 1

    assert len(created_contexts) == 2

    assert main_ctx.enter_count == 1
    assert main_ctx.exit_count == 1
    assert worker_ctx.exit_count == 1


def test_pool_args_returns_expected_initializer() -> None:
    def factory() -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()

    args = stacklib.pool_args(factory)
    assert args["initializer"] is stacklib._pool_initializer
    assert args["initargs"] == (factory, tuple(), {})


def test_pool_initializer_enters_context_and_registers(monkeypatch: pytest.MonkeyPatch) -> None:
    registered_callbacks: list[Callable[..., object]] = []

    def fake_register(callback: Callable[..., object]) -> Callable[..., object]:
        registered_callbacks.append(callback)
        return callback

    monkeypatch.setattr(stacklib.atexit, "register", fake_register)

    ctx = DummyContext()

    def factory() -> DummyContext:
        return ctx

    stacklib._pool_initializer(factory, tuple(), {})

    assert ctx.enter_count == 1
    assert ctx.exit_count == 0
    assert len(registered_callbacks) == 1

    callback = registered_callbacks[0]
    assert getattr(callback, "__self__", None) is ctx

    callback(None, None, None)
    assert ctx.exit_count == 1
