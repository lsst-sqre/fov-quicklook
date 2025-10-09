from __future__ import annotations

import io
import statistics
import time
from dataclasses import dataclass

import astropy.io.fits as pyfits
import numpy

from quicklook.generator.preprocess_ccd.fast_open_comressed_fits import FitsParser


@dataclass
class BenchmarkResult:
    name: str
    timings: list[float]

    @property
    def mean(self) -> float:
        return statistics.fmean(self.timings)

    @property
    def stdev(self) -> float:
        return statistics.pstdev(self.timings)

    def summary(self) -> str:
        return f"{self.name}: {self.mean * 1e3:.2f} ms ± {self.stdev * 1e3:.2f} ms"


def _sample_fits_bytes(size: int = 512, hdus: int = 8) -> bytes:
    rng = numpy.random.default_rng(0)
    primary = pyfits.PrimaryHDU()
    extensions = []
    for index in range(hdus):
        data = rng.normal(loc=1000.0, scale=10.0, size=(size, size)).astype(numpy.float32)
        image_hdu = pyfits.ImageHDU(data=data, name=f'Segment{index:02d}')
        image_hdu.header['BSCALE'] = 1.0
        image_hdu.header['BZERO'] = 0.0
        extensions.append(image_hdu)
    hdul = pyfits.HDUList([primary, *extensions])
    buffer = io.BytesIO()
    hdul.writeto(buffer, overwrite=True)
    return buffer.getvalue()


def _timeit(callable_, iterations: int = 10) -> list[float]:
    timings: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        callable_()
        timings.append(time.perf_counter() - start)
    return timings


def run(iterations: int = 10, size: int = 512, hdus: int = 8) -> list[BenchmarkResult]:
    payload = _sample_fits_bytes(size=size, hdus=hdus)
    results: list[BenchmarkResult] = []

    def legacy_loader() -> None:
        pyfits.HDUList.fromstring(payload)

    def fast_loader() -> None:
        FitsParser(payload).parse()

    results.append(BenchmarkResult('astropy.fromstring', _timeit(legacy_loader, iterations)))
    results.append(BenchmarkResult('fast_open_parser', _timeit(fast_loader, iterations)))
    return results


if __name__ == '__main__':
    for result in run():
        print(result.summary())