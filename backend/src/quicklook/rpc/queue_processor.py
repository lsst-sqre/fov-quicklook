from typing import Any, Callable

from .queue import _RpcQueue


def process_args_kwargs_with_rpc_queue(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    process_queue: Callable[[_RpcQueue, bool], Any],
) -> tuple[list[Any], dict[str, Any]]:
    """
    argsとkwargsを走査してRpcQueueを処理する汎用関数
    
    Args:
        args: 位置引数
        kwargs: キーワード引数
        process_queue: RpcQueueを処理するコールバック関数
            引数: (queue, is_kwarg) → 返り値: 処理済みの値
    
    Returns:
        処理済みのargs, kwargs
    """
    processed_args = []
    for arg in args:
        if isinstance(arg, _RpcQueue):
            processed_args.append(process_queue(arg, False))
        else:
            processed_args.append(arg)

    processed_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, _RpcQueue):
            processed_kwargs[k] = process_queue(v, True)
        else:
            processed_kwargs[k] = v

    return processed_args, processed_kwargs
