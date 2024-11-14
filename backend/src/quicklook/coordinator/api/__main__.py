import logging

import uvicorn

from quicklook.config import config
from quicklook.logging import filter_logs
from quicklook.utils import timeit
from quicklook.utils.uvicorn import uvicorn_add_log_prefix

timeit.settings.logger = logging.getLogger('uvicorn')
filter_logs(["POST /register_generator"])
uvicorn_add_log_prefix(config.dev_log_prefix)
uvicorn.run('quicklook.coordinator.api:app', host='0.0.0.0', port=config.coordinator_port, access_log=True, reload=config.dev_reload)
