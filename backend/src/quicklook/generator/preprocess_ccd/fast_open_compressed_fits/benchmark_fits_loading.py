#!/usr/bin/env python3
"""
FITSファイルの読み込み方法のベンチマーク
"""
from __future__ import annotations

import io
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import astropy.io.fits as pyfits
import mineo_fits_decompress

from quicklook.config import config
from .fast_open_comressed_fits import fast_open_comressed_fits


def benchmark_method(name: str, func: Callable, *args: Any) -> float:
    """メソッドをベンチマークして実行時間を返す"""
    start = time.perf_counter()
    hdul = func(*args)
    # 全HDUのdataにアクセスして遅延評価を強制
    for hdu in hdul:
        _ = hdu.data
    if hasattr(hdul, 'close'):
        hdul.close()
    end = time.perf_counter()
    elapsed = end - start
    print(f"  {name:60s}: {elapsed:8.4f}s")
    return elapsed


def method1_fast_open(filepath: Path) -> Any:
    """fast_open_comressed_fitsを使用"""
    return fast_open_comressed_fits(filepath)


def method2_fromstring(filepath: Path) -> Any:
    """mineo_fits_decompress + astropy.io.fits.HDUList.fromstring"""
    buf = mineo_fits_decompress.decompressed_bytes(filepath, config.fitsio_decompress_parallel)
    return pyfits.HDUList.fromstring(buf)  # type: ignore


def method3_decompress_to_tmpfile(filepath: Path) -> Any:
    """mineo_fits_decompress + /dev/shm + astropy.io.fits.open"""
    buf = mineo_fits_decompress.decompressed_bytes(filepath, config.fitsio_decompress_parallel)
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.fits', dir='/dev/shm', delete=False) as f:
        tmppath = Path(f.name)
        f.write(buf)
    try:
        return pyfits.open(str(tmppath))
    finally:
        # データアクセス後にクリーンアップは benchmark_method で行われる
        try:
            tmppath.unlink()
        except:
            pass


def method4_original_to_tmpfile(filepath: Path) -> Any:
    """元データを/dev/shm + astropy.io.fits.open"""
    with open(filepath, 'rb') as f:
        buf = f.read()
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.fits', dir='/dev/shm', delete=False) as f:
        tmppath = Path(f.name)
        f.write(buf)
    try:
        return pyfits.open(str(tmppath))
    finally:
        try:
            tmppath.unlink()
        except:
            pass


def method5_direct_open(filepath: Path) -> Any:
    """元ファイルを直接astropy.io.fits.openで開く（ベースライン）"""
    return pyfits.open(filepath)


def method6_bytesio_open(filepath: Path) -> Any:
    """mineo_fits_decompress + BytesIO + astropy.io.fits.open"""
    buf = mineo_fits_decompress.decompressed_bytes(filepath, config.fitsio_decompress_parallel)
    return pyfits.open(io.BytesIO(buf))


def method7_memmap_false(filepath: Path) -> Any:
    """元ファイルをmemmap=Falseで開く"""
    return pyfits.open(filepath, memmap=False)


def run_benchmark(filepath: Path, description: str, num_runs: int = 3) -> None:
    """ベンチマークを実行"""
    print(f"\n{'='*80}")
    print(f"Benchmarking: {description}")
    print(f"File: {filepath}")
    print(f"File size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"Number of runs: {num_runs}")
    print(f"{'='*80}")

    methods = [
        ("1. fast_open_comressed_fits", method1_fast_open),
        ("2. mineo_decompress + fromstring", method2_fromstring),
        ("3. mineo_decompress + /dev/shm", method3_decompress_to_tmpfile),
        ("4. original + /dev/shm", method4_original_to_tmpfile),
        ("5. direct open (baseline)", method5_direct_open),
        ("6. mineo_decompress + BytesIO", method6_bytesio_open),
        ("7. direct open memmap=False", method7_memmap_false),
    ]

    all_results = {name: [] for name, _ in methods}

    for run in range(num_runs):
        print(f"\nRun {run + 1}/{num_runs}:")
        for name, func in methods:
            try:
                elapsed = benchmark_method(name, func, filepath)
                all_results[name].append(elapsed)
            except Exception as e:
                print(f"  {name:60s}: ERROR - {e}")
                all_results[name].append(None)

    # 平均を計算
    results = {}
    for name, times in all_results.items():
        valid_times = [t for t in times if t is not None]
        if valid_times:
            results[name] = sum(valid_times) / len(valid_times)
        else:
            results[name] = None

    print(f"\n{'='*80}")
    print(f"Summary (average of {num_runs} runs, sorted by time):")
    print(f"{'='*80}")
    valid_results = [(k, v) for k, v in results.items() if v is not None]
    valid_results.sort(key=lambda x: x[1])

    if valid_results:
        fastest_time = valid_results[0][1]
        for name, elapsed in valid_results:
            ratio = elapsed / fastest_time
            print(f"  {name:60s}: {elapsed:8.4f}s ({ratio:5.2f}x)")


def main() -> None:
    """メイン関数"""
    # テストデータのパス
    test_files = [
        ("Raw FITS (tile-compressed)", Path("./raw_2025092100465-R12_S21.fits")),
    ]

    # preprocess_ccd テストで使われるファイルを探す
    from quicklook.generator.preprocess_ccd import test_preprocess_ccd

    # テストファイルからパスを取得（存在する場合）
    for desc, filepath in test_files:
        if filepath.exists():
            run_benchmark(filepath, desc)
        else:
            print(f"\nSkipping {desc}: file not found at {filepath}")


if __name__ == "__main__":
    main()
