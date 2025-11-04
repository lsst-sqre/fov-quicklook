'''
my_context = Stack[MyContext]()

def enable_my_context():
    with MyContext() as ctx:
        with my_context.push(ctx):
            yield


def f():
    ctx = my_context() # これはpool内の1つのプロセスの中で使いまわされるcontext

with multiprocessing.Pool(**pool_args(enable_my_context)):
    pool.submit(target=f)
'''

import atexit
import contextlib
import threading
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from typing import Callable as TypingCallable
from typing import Generic, ParamSpec, TypeVar

T = TypeVar('T')
P = ParamSpec('P')
Ctx = TypeVar('Ctx', bound=contextlib.AbstractContextManager[object])


@dataclass
class Stack(Generic[T]):
    '''
    単なるstack
    '''

    _stack: list[T] = field(default_factory=list)

    @contextlib.contextmanager
    def push(self, value: T):
        self._stack.append(value)
        try:
            yield
        finally:
            self._stack.pop()

    def __call__(self) -> T:
        if len(self._stack) == 0:
            raise IndexError("Stack is empty")
        return self._stack[-1]


@contextlib.contextmanager
def thread_local_context(f):
    '''
    とあるブロック内でのみ有効なスレッドローカルなコンテキスト
    `requests.Session`などに使う
    '''
    lock = threading.Lock()
    ctx = {}

    def get():
        thread_id = threading.get_ident()
        with lock:
            if thread_id not in ctx:
                c = f()
                stack.enter_context(c)
                ctx[thread_id] = c
            return ctx[thread_id]

    with contextlib.ExitStack() as stack:
        yield get


def pool_args(
    g: TypingCallable[P, Ctx],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> dict[str, Any]:
    # multiprocessing のための引数を作る
    # g は context factory\
    # with multiprocessing.Pool(**pool_args(my_context)):
    #   ...
    # のようにつかう。
    initargs: tuple[object, ...]
    initargs = (g, args, kwargs)
    return {
        'initializer': _pool_initializer,
        'initargs': initargs,
    }


_exit_stacks = set()


def _pool_initializer(g: Callable, args, kwargs) -> None:
    stack = contextlib.ExitStack()
    _exit_stacks.add(stack)
    ctx = g(*args, **kwargs)
    stack.enter_context(ctx)

    def exit():
        _exit_stacks.remove(stack)
        stack.close()

    atexit.register(exit)
