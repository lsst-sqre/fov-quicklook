import multiprocessing as mp
from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI


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
    """
    state = AppState()
    state.manager = mp.Manager()
    state.process_pool = ProcessPoolExecutor()
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
