import contextlib
import multiprocessing
import os
import signal
import socket
import time

import requests
import requests
import uvicorn


@contextlib.contextmanager
def run_uvicorn_app(app: str, *, port: int | None = None, timeout=10, log_prefix='', healthz='/healthz'):
    p = multiprocessing.Process(target=uvicorn_run, args=(app,), kwargs={'port': port, 'log_prefix': log_prefix})
    p.start()

    if port is None:  # pragma: no cover
        port = find_free_tcp_port()

    def wait_for_ready():
        for _ in range(timeout):
            try:
                requests.get(f'http://127.0.0.1:{port}{healthz}')
                break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:  # pragma: no cover
            raise TimeoutError(f'{app} did not start in {timeout} seconds')

    try:
        yield wait_for_ready
    finally:
        assert p.pid
        os.kill(p.pid, signal.SIGINT)  # p.terminate() を使うとcoverageがとれないのでSIGINTを送る
        p.join()


def uvicorn_run(app: str, *, port: int, log_prefix: str):
    uvicorn_add_log_prefix(log_prefix)
    uvicorn.run(app, port=port)


def uvicorn_add_log_prefix(prefix: str):
    log_config = uvicorn.config.LOGGING_CONFIG  # type: ignore
    log_config["formatters"]["default"]["fmt"] = f'{prefix}{log_config["formatters"]["default"]["fmt"]}'


def find_free_tcp_port(host='127.0.0.1') -> int:  # pragma: no cover
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 0 を指定すると OS が未使用のポートを割り当てる
        s.bind((host, 0))
        s.listen(1)  # サーバ用途なら listen しておく
        port = s.getsockname()[1]
    # ← with を抜けるとソケットが閉じるため、この瞬間に他プロセスに取られる可能性がある
    return port
