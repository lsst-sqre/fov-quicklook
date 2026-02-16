"""zipfile（標準） vs isal（C拡張）のベンチマーク

サンプルのZIPファイルを作成し、中のファイルを読み出す速度を比較する。
"""

import os
import time
import zipfile
import tempfile
import statistics

# isal は zipfile の drop-in replacement を提供する
from isal import isal_zlib
import isal.igzip


def create_sample_zip(zip_path: str, num_files: int = 10, file_size_mb: int = 50) -> list[str]:
    """サンプルZIPファイルを作成する。

    FITSファイルに近いサイズ感（各50MB程度）のファイルを複数格納。
    """
    names = []
    print(f"Creating sample ZIP with {num_files} files of ~{file_size_mb}MB each...")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i in range(num_files):
            name = f"data_{i:03d}.bin"
            # ランダムデータだと圧縮しにくいので、構造的なデータを混ぜる
            # （FITSファイルに近い特性を模倣）
            data = os.urandom(file_size_mb * 1024 * 1024 // 2) + bytes(file_size_mb * 1024 * 1024 // 2)
            zf.writestr(name, data)
            names.append(name)
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Created {zip_path}: {zip_size:.1f}MB")
    return names


def benchmark_stdlib_zipfile(zip_path: str, target_name: str, iterations: int = 20) -> list[float]:
    """標準 zipfile モジュールでの読み出し時間を計測"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        with zipfile.ZipFile(zip_path) as zf:
            data = zf.read(target_name)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def benchmark_isal_zipfile(zip_path: str, target_name: str, iterations: int = 20) -> list[float]:
    """isal の igzip を使って zipfile を高速化した読み出し時間を計測

    isal.igzip_lib は zlib の drop-in replacement として使える。
    zipfile._DecompressorクラスにisalのdecompressorをMonkey-patchするか、
    あるいは手動でZIPエントリを読み出す。

    ここでは isal.isal_zlib を使って直接解凍する方法を試す。
    """
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        with open(zip_path, "rb") as f:
            zf = zipfile.ZipFile(f)
            info = zf.getinfo(target_name)
            # isal の decompressor で解凍
            compressed = zf.open(target_name)
            # ↑ これは結局内部で stdlib の zlib を使っているので、
            # 別のアプローチが必要

            # 方法: ZIPのrawデータを取得してisalで解凍
            data = compressed.read()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def benchmark_isal_raw(zip_path: str, target_name: str, iterations: int = 20) -> list[float]:
    """isal.isal_zlib を使って ZIP エントリの raw データを直接解凍する"""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        with zipfile.ZipFile(zip_path) as zf:
            info = zf.getinfo(target_name)
            # raw (compressed) データを取得
            with zf.open(target_name) as member:
                # _fileobj から直接 raw を読むのは難しいので、
                # ZipExtFile をそのまま使う（内部で zlib.decompressobj）

                # 代替: zipfile の内部を使わず、手動でオフセットを計算して読む
                pass

        # 手動でraw解凍
        with open(zip_path, "rb") as f:
            zf2 = zipfile.ZipFile(f)
            info = zf2.getinfo(target_name)
            offset = info.header_offset
            f.seek(offset)
            # ローカルファイルヘッダを読み飛ばす
            fheader = f.read(30)
            fname_len = int.from_bytes(fheader[26:28], "little")
            extra_len = int.from_bytes(fheader[28:30], "little")
            f.read(fname_len + extra_len)

            # compressed data
            compressed_data = f.read(info.compress_size)

            # isal で解凍
            data = isal_zlib.decompress(compressed_data, -15)
            assert len(data) == info.file_size

        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def print_results(name: str, times: list[float], data_size_mb: float):
    median = statistics.median(times)
    mean = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    throughput = data_size_mb / median
    print(f"  {name}:")
    print(f"    median={median*1000:.1f}ms, mean={mean*1000:.1f}ms, stdev={stdev*1000:.1f}ms")
    print(f"    throughput={throughput:.1f} MB/s")
    return median


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "sample.zip")
        names = create_sample_zip(zip_path, num_files=5, file_size_mb=50)
        target = names[2]  # 中間のファイルを使う

        # ウォームアップ（ファイルキャッシュ）
        with zipfile.ZipFile(zip_path) as zf:
            _ = zf.read(target)

        print(f"\nBenchmark: reading '{target}' from ZIP")
        print(f"  file_size in ZIP: ~50MB\n")

        iters = 30

        # 1. stdlib zipfile
        t_stdlib = benchmark_stdlib_zipfile(zip_path, target, iters)
        m_stdlib = print_results("stdlib zipfile", t_stdlib, 50)

        # 2. isal raw decompress
        t_isal = benchmark_isal_raw(zip_path, target, iters)
        m_isal = print_results("isal raw decompress", t_isal, 50)

        speedup = m_stdlib / m_isal
        print(f"\n  Speedup: {speedup:.2f}x")


if __name__ == "__main__":
    main()
