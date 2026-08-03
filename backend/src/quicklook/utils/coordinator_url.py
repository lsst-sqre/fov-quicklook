import os
from urllib.parse import urlsplit, urlunsplit

import quicklook.mylogging
from quicklook.config import config

_COORDINATOR_SERVICE_HOST_ENV = "FOV_QUICKLOOK_COORDINATOR_SERVICE_HOST"
_COORDINATOR_SERVICE_NAME = "fov-quicklook-coordinator"
logger = quicklook.mylogging.getLogger(__name__)
_last_logged_choice: tuple[str, bool, str | None] | None = None


def get_coordinator_base_url() -> str:
    global _last_logged_choice
    base_url = config.coordinator_base_url
    parsed = urlsplit(base_url)
    service_host = os.environ.get(_COORDINATOR_SERVICE_HOST_ENV)
    should_use_service_host = (
        config.comm_use_coordinator_service_host
        and service_host is not None
        and parsed.hostname == _COORDINATOR_SERVICE_NAME
    )
    if not should_use_service_host:
        log_state = (base_url, False, service_host)
        if service_host is not None and log_state != _last_logged_choice:
            logger.info(
                "Using configured coordinator base URL instead of service-host fallback: "
                "base_url=%s service_host=%s enabled=%s",
                base_url,
                service_host,
                config.comm_use_coordinator_service_host,
            )
            _last_logged_choice = log_state
        return base_url

    netloc = service_host if parsed.port is None else f"{service_host}:{parsed.port}"
    resolved_url = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    log_state = (resolved_url, True, service_host)
    if log_state != _last_logged_choice:
        logger.info(
            "Using coordinator service-host fallback: base_url=%s resolved_url=%s service_host=%s",
            base_url,
            resolved_url,
            service_host,
        )
        _last_logged_choice = log_state
    return resolved_url
