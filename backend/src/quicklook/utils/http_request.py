from typing import Any

import aiohttp


async def http_request(method: str, url: str, *, content: bytes | None = None, json: Any | None = None) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, data=content, json=json) as response:
            response.raise_for_status()
            return await response.json()
