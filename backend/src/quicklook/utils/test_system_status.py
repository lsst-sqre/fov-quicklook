"""Tests for system status functionality."""

import pytest
from unittest.mock import patch, mock_open
from quicklook.utils.system_status import (
    ContainerStatus,
    MemoryStats,
    get_container_status,
    get_memory_current,
    get_memory_max,
    get_memory_stats,
    get_cpu_current,
    get_cpu_max,
)


def test_get_memory_current():
    """Test reading memory.current."""
    with patch("builtins.open", mock_open(read_data="1048576")):
        result = get_memory_current()
        assert result == 1048576


def test_get_memory_current_not_available():
    """Test memory.current when file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_memory_current()
        assert result == 0


def test_get_memory_max():
    """Test reading memory.max."""
    with patch("builtins.open", mock_open(read_data="2097152")):
        result = get_memory_max()
        assert result == 2097152


def test_get_memory_max_unlimited():
    """Test memory.max when unlimited."""
    with patch("builtins.open", mock_open(read_data="max")):
        result = get_memory_max()
        assert result == 0


def test_get_memory_max_not_available():
    """Test memory.max when file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_memory_max()
        assert result == 0


def test_get_memory_stats():
    """Test reading memory.stat for detailed breakdown."""
    memory_stat_data = """anon 13458292736
file 23291564032
kernel 1708347392
slab 1368051904
sock 49152
shmem 107360256
file_mapped 1217339392
file_dirty 602112
file_writeback 0
inactive_anon 10084352
active_anon 13540106240
inactive_file 18655068160
active_file 4523290624
unevictable 28299264"""
    
    with patch("builtins.open", mock_open(read_data=memory_stat_data)):
        result = get_memory_stats()
        assert result is not None
        assert isinstance(result, MemoryStats)
        assert result.anon == 13458292736
        assert result.file == 23291564032
        assert result.kernel == 1708347392
        assert result.slab == 1368051904
        assert result.sock == 49152
        assert result.shmem == 107360256
        assert result.file_mapped == 1217339392
        assert result.file_dirty == 602112
        assert result.file_writeback == 0
        assert result.inactive_anon == 10084352
        assert result.active_anon == 13540106240
        assert result.inactive_file == 18655068160
        assert result.active_file == 4523290624
        assert result.unevictable == 28299264


def test_get_memory_stats_not_available():
    """Test memory.stat when file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_memory_stats()
        assert result is None


def test_get_memory_stats_partial_data():
    """Test memory.stat with partial data."""
    memory_stat_data = """anon 1000000
file 2000000"""
    
    with patch("builtins.open", mock_open(read_data=memory_stat_data)):
        result = get_memory_stats()
        assert result is not None
        assert result.anon == 1000000
        assert result.file == 2000000
        assert result.kernel == 0
        assert result.slab == 0


def test_get_cpu_current():
    """Test reading cpu.stat for usage_usec."""
    with patch("builtins.open", mock_open(read_data="usage_usec 123456789\nuser_usec 98765432\nsystem_usec 24691357")):
        result = get_cpu_current()
        assert result == 123456789


def test_get_cpu_current_not_available():
    """Test cpu.stat when file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_cpu_current()
        assert result == 0


def test_get_cpu_max():
    """Test reading cpu.max."""
    with patch("builtins.open", mock_open(read_data="50000 100000")):
        result = get_cpu_max()
        assert result == 50000


def test_get_cpu_max_unlimited():
    """Test cpu.max when unlimited."""
    with patch("builtins.open", mock_open(read_data="max")):
        result = get_cpu_max()
        assert result == 0


def test_get_cpu_max_not_available():
    """Test cpu.max when file doesn't exist."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_cpu_max()
        assert result == 0


def test_container_status_model():
    """Test ContainerStatus model creation."""
    memory_stats = MemoryStats(
        anon=1000000,
        file=2000000,
        kernel=300000,
        slab=400000,
        sock=5000,
        shmem=60000,
        file_mapped=700000,
        file_dirty=8000,
        file_writeback=0,
        inactive_anon=100000,
        active_anon=900000,
        inactive_file=1500000,
        active_file=500000,
        unevictable=10000,
    )
    status = ContainerStatus(
        container_name="test-container",
        memory_max=2097152,
        memory_current=1048576,
        memory_stats=memory_stats,
        cpu_max=50000,
        cpu_current=123456789,
        uptime=3600.0,
    )
    assert status.container_name == "test-container"
    assert status.memory_max == 2097152
    assert status.memory_current == 1048576
    assert status.memory_stats is not None
    assert status.memory_stats.anon == 1000000
    assert status.memory_stats.file == 2000000
    assert status.cpu_max == 50000
    assert status.cpu_current == 123456789
    assert status.uptime == 3600.0


def test_container_status_model_without_memory_stats():
    """Test ContainerStatus model creation without memory_stats."""
    status = ContainerStatus(
        container_name="test-container",
        memory_max=2097152,
        memory_current=1048576,
        memory_stats=None,
        cpu_max=50000,
        cpu_current=123456789,
        uptime=3600.0,
    )
    assert status.container_name == "test-container"
    assert status.memory_stats is None


def test_get_container_status():
    """Test getting complete container status."""
    memory_current_data = "1048576"
    memory_max_data = "2097152"
    memory_stat_data = """anon 1000000
file 2000000
kernel 300000
slab 400000
sock 5000
shmem 60000
file_mapped 700000
file_dirty 8000
file_writeback 0
inactive_anon 100000
active_anon 900000
inactive_file 1500000
active_file 500000
unevictable 10000"""
    cpu_data = "usage_usec 123456789\nuser_usec 98765432\nsystem_usec 24691357"
    cpu_max_data = "50000 100000"

    def mock_file_open(path, *args, **kwargs):
        if "/memory.current" in path:
            return mock_open(read_data=memory_current_data)()
        elif "/memory.max" in path:
            return mock_open(read_data=memory_max_data)()
        elif "/memory.stat" in path:
            return mock_open(read_data=memory_stat_data)()
        elif "/cpu.stat" in path:
            return mock_open(read_data=cpu_data)()
        elif "/cpu.max" in path:
            return mock_open(read_data=cpu_max_data)()
        raise FileNotFoundError(f"Unexpected path: {path}")

    with patch("builtins.open", side_effect=mock_file_open):
        with patch("quicklook.utils.system_status.get_process_uptime", return_value=3600.0):
            with patch("quicklook.utils.system_status.socket.gethostname", return_value="test-container"):
                status = get_container_status()

    assert isinstance(status, ContainerStatus)
    assert status.container_name == "test-container"
    assert status.memory_current == 1048576
    assert status.memory_max == 2097152
    assert status.memory_stats is not None
    assert status.memory_stats.anon == 1000000
    assert status.memory_stats.file == 2000000
    assert status.cpu_current == 123456789
    assert status.cpu_max == 50000
    assert status.uptime == 3600.0


def test_container_status_json_serialization():
    """Test that ContainerStatus can be serialized to JSON."""
    memory_stats = MemoryStats(
        anon=1000000,
        file=2000000,
        kernel=300000,
        slab=400000,
        sock=5000,
        shmem=60000,
        file_mapped=700000,
        file_dirty=8000,
        file_writeback=0,
        inactive_anon=100000,
        active_anon=900000,
        inactive_file=1500000,
        active_file=500000,
        unevictable=10000,
    )
    status = ContainerStatus(
        container_name="test-container",
        memory_max=2097152,
        memory_current=1048576,
        memory_stats=memory_stats,
        cpu_max=50000,
        cpu_current=123456789,
        uptime=3600.0,
    )
    json_data = status.model_dump_json()
    assert "test-container" in json_data
    assert "1048576" in json_data
    assert "1000000" in json_data
    assert "2000000" in json_data
