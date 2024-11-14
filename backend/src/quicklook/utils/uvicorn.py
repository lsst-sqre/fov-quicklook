# test_apis.py の中に書きたいコードだが
# この関数をtest_apis.pyに書くと、なぜかtset_api.pyがtest coverageの対象になってしまうのでここに移動

import uvicorn


def uvicorn_run(app: str, *, port: int, log_prefix: str):
    uvicorn_add_log_prefix(log_prefix)
    uvicorn.run(app, port=port)


def uvicorn_add_log_prefix(prefix: str):
    log_config = uvicorn.config.LOGGING_CONFIG  # type: ignore
    log_config["formatters"]["default"]["fmt"] = f'{prefix}{log_config["formatters"]["default"]["fmt"]}'
