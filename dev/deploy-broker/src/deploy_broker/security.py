from __future__ import annotations

import hmac
import re

from fastapi import HTTPException, Request, status

from .config import Settings

_ARGOCD_TOKEN_RE = re.compile(r"argocd\.token=([^;\"'\s]+)")
_GAFAELFAWR_TOKEN_QUOTED_RE = re.compile(r'gafaelfawr="([^"]+)"')
_GAFAELFAWR_TOKEN_PLAIN_RE = re.compile(r"gafaelfawr=([^;\"'\s]+)")


def extract_argocd_token(curl_command: str) -> str:
    match = _ARGOCD_TOKEN_RE.search(curl_command)
    if not match:
        raise ValueError("curl command does not contain argocd.token")
    return match.group(1)


def extract_app_token(curl_command: str) -> str:
    match = _GAFAELFAWR_TOKEN_QUOTED_RE.search(curl_command)
    if match:
        return match.group(1)

    match = _GAFAELFAWR_TOKEN_PLAIN_RE.search(curl_command)
    if match:
        return match.group(1)

    raise ValueError("curl command does not contain gafaelfawr")


def require_bearer_token(request: Request) -> None:
    if _is_local_unauthenticated_request(request):
        return

    app_state = request.app.state
    settings: Settings = app_state.settings
    expected_token = settings.resolve_api_token()

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )

    provided_token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token",
        )


def _is_local_unauthenticated_request(request: Request) -> bool:
    settings: Settings = request.app.state.settings
    return settings.host == "127.0.0.1" and request.url.hostname == "127.0.0.1"
