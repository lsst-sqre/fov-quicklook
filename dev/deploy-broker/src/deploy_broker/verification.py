from __future__ import annotations

import httpx

from .config import Settings
from .storage import TokenStore


class VerificationClient:
    def __init__(self, settings: Settings, token_store: TokenStore) -> None:
        self._settings = settings
        self._token_store = token_store

    def run_basic_checks(self, mode: str) -> dict[str, object]:
        if mode == "none":
            return {"skipped": True}

        try:
            token = self._token_store.get_app_token()
        except RuntimeError:
            if mode == "auto":
                return {"skipped": True, "reason": "app token unavailable"}
            raise

        headers = {"Cookie": f'gafaelfawr="{token}"'}
        timeout = httpx.Timeout(30)

        with httpx.Client(timeout=timeout) as client:
            healthz = client.get(f"{self._settings.app_base_url}/api/healthz", headers=headers)
            frontend = client.get(f"{self._settings.app_base_url}/", headers=headers)

        return {
            "healthz_ok": healthz.status_code == 200,
            "frontend_ok": frontend.status_code == 200,
            "healthz_status_code": healthz.status_code,
            "frontend_status_code": frontend.status_code,
        }

