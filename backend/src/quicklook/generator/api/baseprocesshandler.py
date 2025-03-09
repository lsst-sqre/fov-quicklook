import multiprocessing
import threading
from multiprocessing.connection import Connection
from typing import Callable, Generic, TypeVar

T = TypeVar('T')  # タスクの型
R = TypeVar('R')  # レスポンスの型


class BaseProcessHandler(Generic[T, R]):
    """
    BaseProcessHandler: A Generic Solution for Running Multiprocessing Tasks with Uvicorn

    Problem Statement:
    -----------------
    When using Uvicorn as an ASGI server, direct use of multiprocessing.Pool and similar
    multiprocessing features can lead to issues due to how Uvicorn manages processes and threads.
    Specifically, attempting to create multiprocessing pools within the Uvicorn worker process
    can result in deadlocks, resource leaks, or unexpected behavior due to the event loop
    and process management conflicts.

    Solution Design:
    --------------
    BaseProcessHandler provides a generic pattern to safely offload CPU-intensive tasks
    to separate processes when running under Uvicorn. It works by:

    1. Creating a dedicated child process using multiprocessing.Process
    2. Establishing bidirectional communication through multiprocessing.Pipe
    3. Providing a context manager interface for clean resource management
    4. Implementing thread-safe task execution with proper locking

    Architecture:
    -----------
    - Main Process (Uvicorn) ←→ Pipe Connection ←→ Worker Process
    The main process sends tasks and receives progress/results through the pipe.

    - The worker process runs a specific target function provided by subclasses
    that defines how to process tasks and report progress.

    - Thread locking ensures that concurrent requests don't interfere with ongoing
    process communication.

    Usage Pattern:
    ------------
    1. Create a subclass of BaseProcessHandler
    2. Implement _get_process_target() to return the specific processing function
    3. Use the subclass as a context manager
    4. Call methods to execute tasks in the separate process

    This pattern allows CPU-intensive operations to run in a separate process while
    maintaining proper communication with the main Uvicorn process, avoiding the
    limitations of direct multiprocessing usage within Uvicorn.
    """
    _comm: Connection
    _server: multiprocessing.Process
    _lock: threading.Lock
    _process_target: Callable[[Connection], None]

    def __init__(self, process_target: Callable[[Connection], None]):
        """プロセス対象関数を指定してハンドラを初期化

        Args:
            process_target: サブプロセスで実行する関数
        """
        self._process_target = process_target

    def __enter__(self):
        self._comm, child_comm = multiprocessing.Pipe()
        self._server = multiprocessing.Process(target=self._get_process_target(), args=(child_comm,))
        self._server.start()
        self._lock = threading.Lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._comm.send(None)
        self._comm.close()
        self._server.join()

    def _get_process_target(self) -> Callable[[Connection], None]:
        """コンストラクタで設定された処理関数を返す"""
        return self._process_target

    def available(self) -> bool:
        """プロセスが利用可能かどうかを返す"""
        return not self._lock.locked()

    def execute_task(self, task: T, *, on_update: Callable[[R | None], None]) -> None:
        """タスクを実行する汎用メソッド（サブクラスでオーバーライド可能）"""
        with self._lock:
            self._comm.send(task)
            while True:
                response = self._comm.recv()
                if response is None:
                    break
                on_update(response)
            on_update(None)
