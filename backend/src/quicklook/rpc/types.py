from dataclasses import dataclass
from typing import Any


class RpcRemoteError(Exception):
    """リモート実行でエラーが発生した際にクライアント側で発生させる例外"""

    def __init__(self, error_type: str, error_message: str, traceback: str):
        self.error_type = error_type
        self.error_message = error_message
        self.traceback = traceback
        super().__init__(f"{error_type}: {error_message}\n{traceback}")


@dataclass
class CallMessage:
    """関数呼び出しメッセージ"""

    type: str  # "call"
    func: Any  # pickle化された関数
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


@dataclass
class YieldMessage:
    """ジェネレータからのyieldメッセージ"""

    type: str  # "yield"
    value: Any


@dataclass
class ReturnMessage:
    """関数の戻り値メッセージ"""

    type: str  # "return"
    value: Any


@dataclass
class ErrorMessage:
    """エラーメッセージ"""

    type: str  # "error"
    error_type: str
    error_message: str
    traceback: str


@dataclass
class QueuePutMessage:
    """キューへのput操作メッセージ"""

    type: str  # "queue_put"
    queue_id: int
    value: Any


@dataclass
class QueueDoneMessage:
    """キューの終了メッセージ"""

    type: str  # "queue_done"
    queue_id: int


Message = (
    CallMessage
    | YieldMessage
    | ReturnMessage
    | ErrorMessage
    | QueuePutMessage
    | QueueDoneMessage
)
