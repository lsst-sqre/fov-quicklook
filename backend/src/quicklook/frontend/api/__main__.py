import uvicorn

from quicklook.config import config
from quicklook.utils.uvicorn import uvicorn_add_log_prefix

uvicorn_add_log_prefix(config.dev_log_prefix)
uvicorn.run('quicklook.frontend.api:app', host='0.0.0.0', port=config.frontend_port, access_log=True, reload=config.dev_reload)
