#!/usr/bin/env python3
from __future__ import annotations

import collections
import os
import signal
import time
from pathlib import Path
from typing import Iterator

ROOT_PID = 2968184
LOG_PATH = Path("log")


def read_children(pid: int) -> list[int]:
    """Return direct child PIDs for the given process."""
    try:
        with open(f"/proc/{pid}/task/{pid}/children", "r", encoding="ascii") as stream:
            data = stream.read().strip()
    except FileNotFoundError:
        return []
    if not data:
        return []
    return [int(part) for part in data.split() if part]


def collect_tree(root: int) -> dict[int, list[int]]:
    tree: dict[int, list[int]] = collections.defaultdict(list)
    seen: set[int] = {root}
    queue: collections.deque[int] = collections.deque([root])
    while queue:
        current = queue.popleft()
        for child in read_children(current):
            tree[current].append(child)
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return tree


def postorder(tree: dict[int, list[int]], root: int) -> Iterator[int]:
    stack: list[tuple[int, bool]] = [(root, False)]
    while stack:
        node, visited = stack.pop()
        if visited:
            yield node
            continue
        stack.append((node, True))
        for child in tree.get(node, []):
            stack.append((child, False))


def wait_for_output(start: int, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout

    def get_log_size():
        try:
            return LOG_PATH.stat().st_size
        except FileNotFoundError:
            return 0

    size = get_log_size()

    while time.monotonic() < deadline:
        size = get_log_size()
        if size > start:
            return size
        time.sleep(0.1)

    return size


def slice_log(start: int, end: int) -> bytes:
    if not LOG_PATH.exists() or end <= start:
        return b""
    with LOG_PATH.open("rb") as stream:
        stream.seek(start)
        return stream.read(end - start)


def dump_segment(pid: int, start: int, end: int) -> None:
    segment = slice_log(start, end)
    if not segment:
        print(f"  no data for {pid}")
        return
    target = Path(f"log.{pid}")
    with target.open("wb") as stream:
        stream.write(segment)
    print(f"  wrote {target}")


def signal_process(pid: int) -> None:
    start_size = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
    print(f"sending SIGUSR1 to {pid}")
    try:
        os.kill(pid, signal.SIGUSR1)
    except ProcessLookupError:
        print(f"  skip {pid}: process missing")
        return
    end_size = wait_for_output(start_size)
    if end_size == start_size:
        print("  no new log output detected")
        return
    time.sleep(0.2)
    dump_segment(pid, start_size, end_size)


def main() -> None:
    LOG_PATH.touch(exist_ok=True)
    tree = collect_tree(ROOT_PID)
    seen = set(tree)
    for parent in list(tree):
        seen.update(tree[parent])
    if ROOT_PID not in seen:
        raise SystemExit(f"root PID {ROOT_PID} not found")

    for pid in postorder(tree, ROOT_PID):
        if pid == ROOT_PID:
            continue
        signal_process(pid)

    signal_process(ROOT_PID)


if __name__ == "__main__":
    main()
