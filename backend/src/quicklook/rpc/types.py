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

    func: Any  # pickle化された関数
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


@dataclass
class ResponseTypeMessage:
    """関数の戻り値の型を示すメッセージ"""

    is_generator: bool


@dataclass
class YieldMessage:
    """ジェネレータからのyieldメッセージ"""

    value: Any


@dataclass
class ReturnMessage:
    """関数の戻り値メッセージ"""

    value: Any


@dataclass
class ErrorMessage:
    """エラーメッセージ"""

    error_type: str
    error_message: str
    traceback: str


@dataclass
class ExitMessage:
    """通信終了メッセージ"""

    pass


@dataclass
class QueuePutMessage:
    """キューへのput操作メッセージ"""

    queue_id: int
    value: Any


@dataclass(frozen=True)
class QueueRef:
    """
    キューへの参照を表すマーカークラス

    整数のqueue_idではなくこのクラスを使うことで、
    通常の整数引数とキューを区別できる
    """

    queue_id: int


Message = (
    CallMessage
    | ResponseTypeMessage
    | YieldMessage
    | ReturnMessage
    | ErrorMessage
    | ExitMessage
    | QueuePutMessage
)
