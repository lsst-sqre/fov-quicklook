import uvicorn

from quicklook.config import config

uvicorn.run(
    'quicklook.frontend.api.app:app',
    host='0.0.0.0',
    port=config.frontend_port,
    access_log=False,
    log_level=config.log_level,
)
