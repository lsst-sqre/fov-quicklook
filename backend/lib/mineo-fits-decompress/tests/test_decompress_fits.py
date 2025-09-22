import time
import contextlib
import io
from pathlib import Path
from typing import Callable
from unittest import skipIf
import astropy.io.fits as pyfits # type: ignore
import mineo_fits_decompress # type: ignore

example_file = Path('/home/michitaro/rubinviewer/data/shots/calexp-192350/calexp_LSSTCam-imSim_i_i_sim_1_4_192350_R23_S12_2_2i_runs_DP0_2_v23_0_0_rc5_PREOPS-905_20211218T041605Z.fits')

n_threads = 8

@skipIf(not example_file.exists(), 'example file does not exist')  
def test_decompress_fits():
    def pyfits_open():
        with pyfits.open(example_file, memmap=False) as hdul:
            for i in [1, 2, 3]:
                hdu = hdul[i]
                hdu.data
    timeit('pyfits.open', pyfits_open)

    def fast_decompress_bytesio():
        b = io.BytesIO(mineo_fits_decompress.decompressed_bytes(example_file, n_threads))
        with pyfits.open(b) as hdul:
            for i in [1, 2, 3]:
                hdu = hdul[i]
                hdu.data
    timeit('fast_decompress_bytesio', fast_decompress_bytesio)

    def fast_decompress_fromstring():
        hdul = pyfits.HDUList.fromstring(mineo_fits_decompress.decompressed_bytes(example_file, n_threads))
        for i in [1, 2, 3]:
            hdu = hdul[i]
            hdu.data
    timeit('fast_decompress_from_string', fast_decompress_fromstring)


def timeit(label: str, f: Callable, times:int=5):
    records: list[float] = []
    for _ in range(times):
        start = time.time()
        f()
        end = time.time()
        records.append(end - start)
    median = sorted(records)[len(records) // 2]
    print(f'{label}: {median}')
