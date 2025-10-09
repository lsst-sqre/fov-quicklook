'''
プロセスツリーのリソース使用状況を表示するためのコマンドライン用スクリプト

次の機能を持つ

* とある起点となるプロセスを指定して、そのプロセスツリーに関する情報を表示。
* プロセスツリーをツリー表示。
* ツリー表示の左側にPID, RSS, PSS(指定時のみ)など各種情報を表示。
* 起点となるプロセスは複数指定可能。
* 起点プロセスはプロセス名（引数含む）に対するパターン（反パターン）で指定可能。

実装時の注意

再利用可能な単位で関数に分けて実装する。
'''

import argparse
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import NewType

PID = NewType('PID', int)
KBSize = NewType('KBSize', int)


@dataclass
class ProcessInfo:
    """プロセスの情報を保持するデータクラス"""

    pid: PID
    ppid: PID
    name: str
    cmdline: str
    rss: KBSize  # KB
    pss: KBSize | None = None  # KB (利用可能な場合のみ)


def get_process_info(pid: int, include_pss: bool = False) -> ProcessInfo | None:
    """指定されたPIDのプロセス情報を取得"""
    try:
        proc_path: Path = Path(f"/proc/{pid}")

        # stat から PID, PPID, 名前を取得
        stat_content: str = (proc_path / "stat").read_text()
        parts: list[str] = stat_content.split()
        ppid: int = int(parts[3])
        name: str = parts[1].strip("()")

        # cmdline を取得
        cmdline_content: str = (proc_path / "cmdline").read_text()
        cmdline: str = cmdline_content.replace("\0", " ").strip()
        if not cmdline:
            cmdline = f"[{name}]"

        # statm から RSS を取得 (ページ単位)
        statm_content: str = (proc_path / "statm").read_text()
        statm_parts: list[str] = statm_content.split()
        rss_pages: int = int(statm_parts[1])
        page_size: int = 4  # KB
        rss: int = rss_pages * page_size

        # PSS を取得 (オプション)
        pss: int | None = None
        if include_pss:
            try:
                smaps_content: str = (proc_path / "smaps_rollup").read_text()
                for line in smaps_content.splitlines():
                    if line.startswith("Pss:"):
                        pss = int(line.split()[1])
                        break
            except FileNotFoundError:
                pass

        return ProcessInfo(PID(pid), PID(ppid), name, cmdline, KBSize(rss), KBSize(pss) if pss is not None else None)

    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
        return None


def get_all_processes(include_pss: bool = False) -> dict[PID, ProcessInfo]:
    """システム内の全プロセス情報を取得"""
    proc_dir: Path = Path("/proc")

    # PIDのリストを作成
    pids: list[int] = []
    for pid_dir in proc_dir.iterdir():
        if pid_dir.is_dir() and pid_dir.name.isdigit():
            pids.append(int(pid_dir.name))

    # ThreadPoolExecutorを使って並列処理
    processes: dict[PID, ProcessInfo] = {}
    with ThreadPoolExecutor() as executor:
        # 各PIDの処理を並列実行
        futures = {executor.submit(get_process_info, pid, include_pss): pid for pid in pids}
        for future in futures:
            pid: int = futures[future]
            info: ProcessInfo | None = future.result()
            if info:
                processes[PID(pid)] = info

    return processes


def build_process_tree(processes: dict[PID, ProcessInfo]) -> dict[PID, list[PID]]:
    """親プロセスから子プロセスへのマッピングを構築"""
    tree: dict[PID, list[PID]] = {}
    for pid, info in processes.items():
        if info.ppid not in tree:
            tree[info.ppid] = []
        tree[info.ppid].append(pid)
    return tree


def get_process_subtree(root_pid: PID, tree: dict[PID, list[PID]]) -> set[PID]:
    """指定されたプロセスを起点とするサブツリーの全PIDを取得"""
    result: set[PID] = {root_pid}

    def traverse(pid: PID):
        if pid in tree:
            for child_pid in tree[pid]:
                result.add(child_pid)
                traverse(child_pid)

    traverse(root_pid)
    return result


def match_process(info: ProcessInfo, patterns: list[str], exclude_patterns: list[str]) -> bool:
    """プロセスがパターンにマッチするか判定"""
    full_cmd = f"{info.name} {info.cmdline}"

    # 除外パターンにマッチする場合は除外
    for pattern in exclude_patterns:
        if re.search(pattern, full_cmd):
            return False

    # パターンが指定されていない場合は全てマッチ
    if not patterns:
        return True

    # いずれかのパターンにマッチ
    for pattern in patterns:
        if re.search(pattern, full_cmd):
            return True

    return False


def find_root_processes(
    processes: dict[PID, ProcessInfo], patterns: list[str], exclude_patterns: list[str]
) -> list[PID]:
    """指定されたパターンにマッチするプロセスを検索"""
    matching_pids: list[PID] = []

    for pid, info in processes.items():
        if match_process(info, patterns, exclude_patterns):
            matching_pids.append(pid)

    return matching_pids


def filter_deep_processes(pids: list[PID], processes: dict[PID, ProcessInfo]) -> list[PID]:
    """
    プロセスリストから、親子関係にあるプロセスを除外し、最も浅い（rootに近い）プロセスのみを返す

    例: [親PID, 子PID, 孫PID] の場合、[親PID] のみを返す
    """
    # 自分の親プロセスの中に他のpidがなければよい
    roots: list[PID] = []

    for pid in pids:
        if all(other_pid not in parent_process_ids(pid, processes) for other_pid in pids if other_pid != pid):
            roots.append(pid)
    return roots


def parent_process_ids(pid: PID, processes: dict[PID, ProcessInfo]) -> list[PID]:
    ppids: list[PID] = []
    while True:
        if pid not in processes:
            break
        ppids.append(processes[pid].pid)
        pid = processes[pid].ppid
    return ppids


def format_size(kb: int) -> str:
    """サイズを人間が読みやすい形式にフォーマット"""
    if kb < 1024:
        return f"{kb}K"
    elif kb < 1024 * 1024:
        return f"{kb / 1024:.1f}M"
    else:
        return f"{kb / (1024 * 1024):.1f}G"


def truncate_cmdline(cmdline: str, max_length: int = 80) -> str:
    """コマンドラインを指定された長さにtruncate"""
    if len(cmdline) <= max_length:
        return cmdline
    return cmdline[:max_length - 3] + "..."


def parse_cmdline(cmdline: str) -> tuple[str, str]:
    """コマンドラインをコマンド名と引数に分ける"""
    parts: list[str] = cmdline.split()
    if not parts:
        return "", ""
    command: str = parts[0]
    args: str = " ".join(parts[1:])
    return command, args


def colorize_cmdline(command: str, args: str) -> str:
    """コマンド名を太字白、引数を薄い色で色付け"""
    if not args:
        return f"\033[1;37m{command}\033[0m"
    return f"\033[1;37m{command}\033[0m \033[2m{args}\033[0m"


def get_memory_color(kb: int) -> str:
    """メモリ使用量に応じて色を返す"""
    if kb <= 102400:  # 100MB
        return "\033[32m"
    elif kb <= 1048576:  # 1GB
        return "\033[33m"
    else:
        return "\033[31m"


def print_process_tree(
    root_pid: PID,
    processes: dict[PID, ProcessInfo],
    tree: dict[PID, list[PID]],
    include_pss: bool = False,
    prefix: str = "",
    is_last: bool = True,
    truncate: bool = True,
    color: bool = True,
    truncate_length: int = 80,
    header_len: int = 30,
    terminal_width: int = 80,
):
    """プロセスツリーを再帰的に表示"""
    if root_pid not in processes:
        return

    info: ProcessInfo = processes[root_pid]

    # ツリー構造の記号
    connector: str = "└── " if is_last else "├── "

    # プロセス情報の表示
    rss_str: str = format_size(info.rss)
    stats: str = f"{info.pid:<8}"
    if color:
        rss_color: str = get_memory_color(info.rss)
        stats += f" {rss_color}{rss_str:>8}\033[0m"
    else:
        stats += f" {rss_str:>8}"
    if include_pss and info.pss is not None:
        pss_str: str = format_size(info.pss)
        if color:
            pss_color: str = get_memory_color(info.pss)
            stats += f" {pss_color}{pss_str:>8}\033[0m"
        else:
            stats += f" {pss_str:>8}"
    elif include_pss:
        stats += " " * 9

    tree_start: int = len(stats) + 2  # RSSの後2文字開ける

    cmdline_display: str = info.cmdline
    if truncate:
        # インデントによって表示可能文字数を計算
        current_prefix: str = stats.ljust(tree_start) + prefix + connector
        available_length: int = max(10, terminal_width - len(current_prefix))
        cmdline_display = truncate_cmdline(info.cmdline, max_length=available_length)
    if color:
        command, args = parse_cmdline(cmdline_display)
        cmdline_display = colorize_cmdline(command, args)

    tree_part: str = f"{prefix}{connector}{cmdline_display}"
    tree_start: int = len(stats) + 2  # RSSの後2文字開ける
    stats_padded: str = stats.ljust(tree_start)
    print(f"{stats_padded}{tree_part}")

    # 子プロセスを再帰的に表示
    if root_pid in tree:
        children: list[PID] = tree[root_pid]
        extension: str = "    " if is_last else "│   "

        for i, child_pid in enumerate(children):
            is_last_child: bool = i == len(children) - 1
            print_process_tree(child_pid, processes, tree, include_pss, prefix + extension, is_last_child, truncate, color, truncate_length, header_len, terminal_width)


def calculate_subtree_stats(
    root_pid: PID, processes: dict[PID, ProcessInfo], subtree_pids: set[PID]
) -> tuple[KBSize, KBSize | None]:
    """サブツリー全体のRSSとPSSの合計を計算"""
    total_rss: int = 0
    total_pss: int | None = (
        0 if any(processes[pid].pss is not None for pid in subtree_pids if pid in processes) else None
    )

    for pid in subtree_pids:
        if pid in processes:
            info: ProcessInfo = processes[pid]
            total_rss += info.rss
            if total_pss is not None and info.pss is not None:
                total_pss += info.pss

    return KBSize(total_rss), KBSize(total_pss) if total_pss is not None else None


def clear_screen():
    """画面をクリア"""
    os.system('clear')


def display_processes(
    root_pids: list[PID], processes: dict[PID, ProcessInfo], tree: dict[PID, list[PID]], include_pss: bool, truncate: bool, color: bool
):
    """プロセスツリーを表示"""
    terminal_width: int = shutil.get_terminal_size().columns
    truncate_length: int = max(40, terminal_width - 50)  # 最低40文字

    for root_pid in root_pids:
        if root_pid not in processes:
            print(f"PID {root_pid} のプロセスが見つかりません")
            continue

        # サブツリーの統計を計算
        subtree_pids: set[PID] = get_process_subtree(root_pid, tree)
        total_rss: KBSize
        total_pss: KBSize | None
        total_rss, total_pss = calculate_subtree_stats(root_pid, processes, subtree_pids)

        # ヘッダー構築
        header: str = f"{'PID':<8} {'RSS':>8}"
        if include_pss:
            header += f" {'PSS':>8}"
        header += " Tree"
        header_len: int = len(header)

        # ヘッダー表示
        print(f"\n{'=' * terminal_width}")
        print(f"プロセスツリー (起点: PID {root_pid})")
        print(f"プロセス数: {len(subtree_pids)}")
        if color:
            rss_color: str = get_memory_color(total_rss)
            print(f"合計 RSS: {rss_color}{format_size(total_rss)}\033[0m")
            if total_pss is not None:
                pss_color: str = get_memory_color(total_pss)
                print(f"合計 PSS: {pss_color}{format_size(total_pss)}\033[0m")
        else:
            print(f"合計 RSS: {format_size(total_rss)}")
            if total_pss is not None:
                print(f"合計 PSS: {format_size(total_pss)}")
        print(f"{'=' * terminal_width}")
        print(header)
        print("-" * terminal_width)

        # ツリー表示
        print_process_tree(root_pid, processes, tree, include_pss, truncate=truncate, color=color, truncate_length=truncate_length, header_len=header_len, terminal_width=terminal_width)


def main():
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="プロセスツリーのリソース使用状況を表示")
    parser.add_argument("-p", "--pid", type=int, action="append", help="起点となるプロセスのPID（複数指定可能）")
    parser.add_argument(
        "-n",
        "--pattern",
        type=str,
        action="append",
        default=[],
        help="プロセス名やコマンドラインにマッチする正規表現パターン（複数指定可能）",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        type=str,
        action="append",
        default=[],
        help="除外するプロセスの正規表現パターン（複数指定可能）",
    )
    parser.add_argument("--pss", action="store_true", help="PSS（Proportional Set Size）も表示")
    parser.add_argument(
        "-w", "--watch", type=float, metavar="INTERVAL", help="指定された秒数ごとに自動更新（watchモード）"
    )
    parser.add_argument("--no-truncate", action="store_true", help="コマンドラインをtruncateしない")
    parser.add_argument("--no-color", action="store_true", help="色付けを無効化")

    args = parser.parse_args()

    # watchモードの場合
    if args.watch:
        try:
            while True:

                # プロセス情報を取得
                processes: dict[PID, ProcessInfo] = get_all_processes(include_pss=args.pss)
                tree: dict[PID, list[PID]] = build_process_tree(processes)

                # 起点となるプロセスを決定
                if args.pid:
                    root_pids: list[PID] = [PID(pid) for pid in args.pid]
                else:
                    # パターンにマッチするプロセスを検索
                    root_pids: list[PID] = find_root_processes(processes, args.pattern, args.exclude)
                    # 重複を除外（最も深いプロセスのみ）
                    root_pids = filter_deep_processes(root_pids, processes)

                # プロセスツリーを表示
                clear_screen()
                display_processes(root_pids, processes, tree, args.pss, not args.no_truncate, not args.no_color)
                print()
                print(f"更新時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"自動更新モード（{args.watch}秒ごと） - Ctrl+C で終了")

                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n終了しました")
            return

    # 通常モード（1回のみ表示）
    print("プロセス情報を取得中...")
    processes: dict[PID, ProcessInfo] = get_all_processes(include_pss=args.pss)
    tree: dict[PID, list[PID]] = build_process_tree(processes)

    # 起点となるプロセスを決定
    if args.pid:
        root_pids: list[PID] = [PID(pid) for pid in args.pid]
    else:
        # パターンにマッチするプロセスを検索
        root_pids: list[PID] = find_root_processes(processes, args.pattern, args.exclude)
        # 重複を除外（最も深浅いロセスのみ）
        root_pids = filter_deep_processes(root_pids, processes)

        if not root_pids:
            print("マッチするプロセスが見つかりませんでした")
            return

    # プロセスツリーを表示
    display_processes(root_pids, processes, tree, args.pss, not args.no_truncate, not args.no_color)


if __name__ == "__main__":
    main()
