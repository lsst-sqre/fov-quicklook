from __future__ import annotations

import pytest

from deploy_broker.security import extract_app_token, extract_argocd_token


def test_extract_argocd_token_from_curl_command() -> None:
    curl_command = (
        "curl 'https://example.invalid' "
        "-H 'Cookie: argocd.token=abc123.def456; other=value'"
    )

    assert extract_argocd_token(curl_command) == "abc123.def456"


def test_extract_app_token_supports_quoted_cookie() -> None:
    curl_command = (
        "curl 'https://example.invalid' "
        '-H \'Cookie: gafaelfawr="quoted-token"; other=value\''
    )

    assert extract_app_token(curl_command) == "quoted-token"


def test_extract_app_token_supports_plain_cookie() -> None:
    curl_command = (
        "curl 'https://example.invalid' "
        "-H 'Cookie: gafaelfawr=plain-token; other=value'"
    )

    assert extract_app_token(curl_command) == "plain-token"


def test_extract_argocd_token_raises_for_missing_cookie() -> None:
    with pytest.raises(ValueError):
        extract_argocd_token("curl 'https://example.invalid'")

