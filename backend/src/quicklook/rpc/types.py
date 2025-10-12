from typing import Any, TypedDict


class RpcRemoteError(Exception):
    """リモート実行でエラーが発生した際にクライアント側で発生させる例外"""

    def __init__(self, error_type: str, error_message: str, traceback: str):
        self.error_type = error_type
        self.error_message = error_message
        self.traceback = traceback
        super().__init__(f"{error_type}: {error_message}\n{traceback}")


class CallMessage(TypedDict):
    """関数呼び出しメッセージ"""

    type: str  # "call"
    func: Any  # pickle化された関数
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class YieldMessage(TypedDict):
    """ジェネレータからのyieldメッセージ"""

    type: str  # "yield"
    value: Any


class ReturnMessage(TypedDict):
    """関数の戻り値メッセージ"""

    type: str  # "return"
    value: Any


class ErrorMessage(TypedDict):
    """エラーメッセージ"""

    type: str  # "error"
    error_type: str
    error_message: str
    traceback: str


class QueuePutMessage(TypedDict):
    """キューへのput操作メッセージ"""

    type: str  # "queue_put"
    queue_id: int
    value: Any


class QueueDoneMessage(TypedDict):
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
