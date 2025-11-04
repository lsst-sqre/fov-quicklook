from quicklook.config import config

import uvicorn

uvicorn.run(
    'quicklook.generator.api.app:app',
    host='0.0.0.0',
    port=config.generator_port,
    access_log=False,
    log_level=config.log_level,
)
