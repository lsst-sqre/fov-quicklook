from dataclasses import dataclass
import asyncio
import socket


@dataclass
class DiskInfo:
    mount_point: str
    total: int
    used: int
    device: str


@dataclass
class PodStatus:
    hostname: str
    memory_total: int
    memory_used: int
    disks: list[DiskInfo]


async def get_memory_info() -> tuple[int, int]:
    proc = await asyncio.create_subprocess_exec('vmstat', '-s', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    lines = stdout.decode().split('\n')
    stats = {' '.join(line.split()[1:]): int(line.split()[0]) for line in lines if line.strip()}

    memory_total = stats['K total memory'] * 1024
    memory_used = stats['K used memory'] * 1024
    return memory_total, memory_used


async def get_disk_info() -> list[DiskInfo]:
    proc = await asyncio.create_subprocess_exec('df', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    lines = stdout.decode().strip().split('\n')
    
    disks = []
    # 最初の行はヘッダーなので2行目から処理
    for line in lines[1:]:
        if not line.strip():
            continue
        try:
            parts = line.split()
            if len(parts) < 6:  # dfの出力は少なくとも6カラムある
                continue
            disks.append(DiskInfo(
                device=parts[0],
                mount_point=parts[5],
                total=int(parts[1]) * 1024,
                used=int(parts[2]) * 1024
            ))
        except (IndexError, ValueError):
            continue
    return disks


async def pod_status() -> PodStatus:
    memory_info, disk_info = await asyncio.gather(get_memory_info(), get_disk_info())
    hostname = socket.gethostname()

    return PodStatus(hostname=hostname, memory_total=memory_info[0], memory_used=memory_info[1], disks=disk_info)
