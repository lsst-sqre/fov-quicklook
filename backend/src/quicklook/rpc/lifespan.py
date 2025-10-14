from collections.abc import AsyncIterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI


class AppState:
    """FastAPIアプリケーションの状態を保持するクラス"""

    def __init__(self):
        self.process_pool: ProcessPoolExecutor | None = None


@asynccontextmanager
async def rpc_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPIのlifespanで使用するコンテキストマネージャ
    
    アプリケーション起動時にProcessPoolExecutorを作成し、
    終了時にクリーンアップを行う。
    """
    state = AppState()
    state.process_pool = ProcessPoolExecutor()
    app.state.rpc = state
    
    try:
        yield
    finally:
        if state.process_pool:
            state.process_pool.shutdown(wait=True)


def get_process_pool(app: FastAPI) -> ProcessPoolExecutor:
    """アプリケーションからProcessPoolExecutorを取得する"""
    state: AppState = app.state.rpc
    if state.process_pool is None:  # pragma: no branch
        raise RuntimeError("Process pool is not initialized")
    return state.process_pool
