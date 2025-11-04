import atexit
import multiprocessing as mp
from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager, ExitStack
from typing import Any

from fastapi import FastAPI

from quicklook.comm.generator import GeneratorIdInitializer, self_generator_id
from quicklook.config import config


_exit_stacks: set[ExitStack] = set()


def _initialize_rpc_worker(initializers: list):
    """RPC ProcessPoolExecutorのワーカープロセス初期化"""
    stack = ExitStack()
    for init in initializers:
        stack.enter_context(init())
    
    _exit_stacks.add(stack)
    
    def exit_handler():  # pragma: no cover
        _exit_stacks.remove(stack)
        stack.close()
    
    atexit.register(exit_handler)


class AppState:
    """FastAPIアプリケーションの状態を保持するクラス"""

    def __init__(self):
        self.process_pool: ProcessPoolExecutor | None = None
        self.manager: Any = None  # mp.Manager type


@asynccontextmanager
async def rpc_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPIのlifespanで使用するコンテキストマネージャ
    
    アプリケーション起動時にProcessPoolExecutorとManagerを作成し、
    終了時にクリーンアップを行う。
    
    ProcessPoolExecutorはspawnで起動し、各ワーカーでGeneratorIDを初期化する。
    これにより、ワーカープロセスはクリーンな状態で開始され、
    その中でmultiprocessing.Poolをforkで作成しても安全。
    """
    state = AppState()
    state.manager = mp.Manager()
    ctx = mp.get_context('spawn')
    
    # GeneratorIDをワーカープロセスで初期化
    initializers = [GeneratorIdInitializer()]
    
    state.process_pool = ProcessPoolExecutor(
        max_workers=config.rpc_process_pool_workers,
        mp_context=ctx,
        initializer=_initialize_rpc_worker,
        initargs=(initializers,),
    )
    app.state.rpc = state
    
    try:
        yield
    finally:
        if state.process_pool:
            state.process_pool.shutdown(wait=True)
        if state.manager:
            state.manager.shutdown()  # type: ignore[attr-defined]


def get_process_pool(app: FastAPI) -> ProcessPoolExecutor:
    """アプリケーションからProcessPoolExecutorを取得する"""
    state: AppState = app.state.rpc
    if state.process_pool is None:  # pragma: no branch
        raise RuntimeError("Process pool is not initialized")
    return state.process_pool


def get_manager(app: FastAPI) -> Any:
    """アプリケーションからmultiprocessing.Managerを取得する"""
    state: AppState = app.state.rpc
    if state.manager is None:  # pragma: no branch
        raise RuntimeError("Manager is not initialized")
    return state.manager
