from unittest.mock import patch, AsyncMock
import pytest
from quicklook.utils.podstatus import pod_status, PodStatus, DiskInfo


@pytest.mark.asyncio
async def test_pod_status():
    vmstat_output = b"""
         4001796 K total memory
         2001796 K used memory
    """
    df_output = b"""
    Filesystem     1K-blocks    Used Available Use% Mounted on
    /dev/sda1      61411456 20123456  41288000  33% /
    /dev/sdb1      30000000 15000000  15000000  50% /data
    """

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (vmstat_output, b"")

    mock_proc2 = AsyncMock()
    mock_proc2.communicate.return_value = (df_output, b"")

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_proc, mock_proc2]), \
         patch("socket.gethostname", return_value="test-host"):
        
        result = await pod_status()
        
        assert isinstance(result, PodStatus)
        assert result.hostname == "test-host"
        assert result.memory_total == 4001796 * 1024
        assert result.memory_used == 2001796 * 1024
        assert len(result.disks) == 2
        
        root_disk = next(d for d in result.disks if d.mount_point == "/")
        assert root_disk.device == "/dev/sda1"
        assert root_disk.total == 61411456 * 1024
        assert root_disk.used == 20123456 * 1024

        data_disk = next(d for d in result.disks if d.mount_point == "/data")
        assert data_disk.device == "/dev/sdb1"
        assert data_disk.total == 30000000 * 1024
        assert data_disk.used == 15000000 * 1024
