import os
from urllib.parse import urlsplit, urlunsplit

from quicklook.config import config

_COORDINATOR_SERVICE_HOST_ENV = "FOV_QUICKLOOK_COORDINATOR_SERVICE_HOST"
_COORDINATOR_SERVICE_NAME = "fov-quicklook-coordinator"


def get_coordinator_base_url() -> str:
    base_url = config.coordinator_base_url
    parsed = urlsplit(base_url)
    service_host = os.environ.get(_COORDINATOR_SERVICE_HOST_ENV)
    if service_host is None or parsed.hostname != _COORDINATOR_SERVICE_NAME:
        return base_url

    netloc = service_host if parsed.port is None else f"{service_host}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
