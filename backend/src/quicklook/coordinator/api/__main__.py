from urllib.parse import urlparse

import uvicorn

from quicklook.config import config

parsed = urlparse(config.coordinator_base_url)
port = parsed.port
assert port

uvicorn.run(
    'quicklook.coordinator.api.app:app',
    host='0.0.0.0',
    port=port,
    access_log=False,
    log_level=config.log_level,
)
