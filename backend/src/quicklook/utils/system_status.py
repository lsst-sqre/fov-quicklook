"""System status monitoring utilities for containers."""

import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, Field


class MemoryStats(BaseModel):
    """Detailed memory statistics from cgroup memory.stat."""

    anon: int = Field(
        description="Anonymous memory usage in bytes (private memory not backed by files)"
    )
    file: int = Field(
        description="File-backed memory usage in bytes (page cache)"
    )
    kernel: int = Field(description="Kernel memory usage in bytes")
    slab: int = Field(
        description="Slab memory usage in bytes (kernel data structures)"
    )
    sock: int = Field(description="Socket buffer memory usage in bytes")
    shmem: int = Field(description="Shared memory usage in bytes")
    file_mapped: int = Field(
        description="Memory-mapped file pages in bytes"
    )
    file_dirty: int = Field(
        description="Dirty file-backed pages waiting to be written in bytes"
    )
    file_writeback: int = Field(
        description="File-backed pages currently being written back in bytes"
    )
    inactive_anon: int = Field(
        description="Inactive anonymous memory in bytes (candidates for swapping)"
    )
    active_anon: int = Field(
        description="Active anonymous memory in bytes (recently accessed)"
    )
    inactive_file: int = Field(
        description="Inactive file-backed memory in bytes (candidates for reclaim)"
    )
    active_file: int = Field(
        description="Active file-backed memory in bytes (recently accessed)"
    )
    unevictable: int = Field(
        description="Unevictable memory in bytes (locked, cannot be swapped)"
    )


class ContainerStatus(BaseModel):
    """System status of a container."""

    container_name: str = Field(description="Container hostname")
    memory_max: int = Field(
        description="Memory limit in bytes (0 if unlimited)"
    )
    memory_current: int = Field(
        description="Current total memory usage in bytes"
    )
    memory_stats: MemoryStats | None = Field(
        description="Detailed memory breakdown from cgroup memory.stat"
    )
    cpu_max: int = Field(
        description="CPU quota in microseconds per period (0 if unlimited)"
    )
    cpu_current: int = Field(
        description="Accumulated CPU usage time in microseconds since container start"
    )
    uptime: float = Field(
        description="Container uptime in seconds since boot"
    )


def read_cgroup_file(path: str) -> str | None:
    """Read cgroup file and return content, or None if not available."""
    try:
        with open(path) as f:
            return f.read().strip()
    except (FileNotFoundError, OSError):
        return None


def get_memory_current() -> int:
    """Get current memory usage in bytes."""
    content = read_cgroup_file('/sys/fs/cgroup/memory.current')
    if content is None:
        return 0
    try:
        return int(content)
    except ValueError:
        return 0


def get_memory_max() -> int:
    """Get memory limit in bytes. Returns 0 if unlimited."""
    content = read_cgroup_file('/sys/fs/cgroup/memory.max')
    if content is None or content == 'max':
        return 0
    try:
        return int(content)
    except ValueError:
        return 0


def get_memory_stats() -> MemoryStats | None:
    """Get detailed memory statistics from memory.stat."""
    content = read_cgroup_file('/sys/fs/cgroup/memory.stat')
    if content is None:
        return None

    stats: dict[str, int] = {}
    for line in content.split('\n'):
        parts = line.split()
        if len(parts) == 2:
            key, value = parts
            try:
                stats[key] = int(value)
            except ValueError:
                continue

    try:
        return MemoryStats(
            anon=stats.get('anon', 0),
            file=stats.get('file', 0),
            kernel=stats.get('kernel', 0),
            slab=stats.get('slab', 0),
            sock=stats.get('sock', 0),
            shmem=stats.get('shmem', 0),
            file_mapped=stats.get('file_mapped', 0),
            file_dirty=stats.get('file_dirty', 0),
            file_writeback=stats.get('file_writeback', 0),
            inactive_anon=stats.get('inactive_anon', 0),
            active_anon=stats.get('active_anon', 0),
            inactive_file=stats.get('inactive_file', 0),
            active_file=stats.get('active_file', 0),
            unevictable=stats.get('unevictable', 0),
        )
    except Exception:
        return None


def get_cpu_current() -> int:
    """Get CPU accumulated usage time in microseconds."""
    content = read_cgroup_file('/sys/fs/cgroup/cpu.stat')
    if content is None:
        return 0
    for line in content.split('\n'):
        if line.startswith('usage_usec'):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def get_cpu_max() -> int:
    """Get CPU limit in microseconds. Returns 0 if unlimited."""
    content = read_cgroup_file('/sys/fs/cgroup/cpu.max')
    if content is None or content == 'max':
        return 0
    try:
        parts = content.split()
        return int(parts[0])
    except (IndexError, ValueError):
        return 0


def get_container_status() -> ContainerStatus:
    """Get the current container status."""
    hostname = socket.gethostname()
    return ContainerStatus(
        container_name=hostname,
        memory_max=get_memory_max(),
        memory_current=get_memory_current(),
        memory_stats=get_memory_stats(),
        cpu_max=get_cpu_max(),
        cpu_current=get_cpu_current(),
        uptime=get_process_uptime(),
    )


def get_process_uptime() -> float:
    """Get process uptime in seconds since boot.

    Reads /proc/1/stat to get the process start time in clock ticks,
    then converts it to seconds using the system clock tick rate.
    """
    try:
        with open('/proc/1/stat') as f:
            stat_line = f.read()

        fields = stat_line.split()
        if len(fields) < 22:
            return 0.0

        starttime_ticks = int(fields[21])

        clock_ticks_per_sec = os.sysconf('SC_CLK_TCK')
        if clock_ticks_per_sec <= 0:
            return 0.0

        with open('/proc/uptime') as f:
            system_uptime = float(f.read().split()[0])

        process_start_time = starttime_ticks / clock_ticks_per_sec
        return max(0.0, system_uptime - process_start_time)

    except (OSError, ValueError, IndexError):
        return 0.0
