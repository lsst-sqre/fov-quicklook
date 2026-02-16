from typing import Any

from quicklook.utils.http_client import get_session


async def http_request(method: str, url: str, *, content: bytes | None = None, json: Any | None = None) -> Any:
    session = get_session()
    async with session.request(method, url, data=content, json=json) as response:
            response.raise_for_status()
            return await response.json()
