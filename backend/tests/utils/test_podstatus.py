from unittest.mock import patch, AsyncMock
import pytest
from quicklook.utils.podstatus import get_disk_info, get_memory_info, pod_status


async def test_get_disk_info():
    result = await get_disk_info(dirs=['/'])
    assert len(result) == 1


async def test_get_memory_info():
    total, used = await get_memory_info()
    assert total >= used


async def test_pod_status():
    await pod_status(storage_dirs=['/'])
