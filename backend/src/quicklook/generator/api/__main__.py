import logging

import uvicorn

from quicklook.config import config
from quicklook.logging import filter_logs
from quicklook.utils import timeit
from quicklook.utils.uvicorn import uvicorn_add_log_prefix

from . import GeneratorRuntimeSettings

timeit.settings.logger = logging.getLogger('uvicorn')
filter_logs(["GET /healthz"])
uvicorn_add_log_prefix(config.dev_log_prefix)
uvicorn.run(
    'quicklook.generator.api:app',
    host='0.0.0.0',
    port=GeneratorRuntimeSettings.stack.top.port,
    access_log=False,
    reload=config.dev_reload,
)
