from quicklook.utils.podstatus import get_disk_info, get_memory_info, pod_status, get_ip_address


async def test_get_disk_info():
    result = await get_disk_info(dirs=['/'])
    assert len(result) == 1


async def test_get_memory_info():
    total, used = await get_memory_info()
    assert total >= used


async def test_pod_status():
    await pod_status(storage_dirs=['/'])


async def test_get_ip_address():
    ip_addr = await get_ip_address()
    assert ip_addr
    [
        ip,
    ] = ip_addr.split()
    assert len(ip.split('.')) == 4
