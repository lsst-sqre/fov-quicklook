import io
import mineo_fits_decompress
import contextlib
import functools
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import astropy.io.fits as afits
import numpy

from quicklook.generator.isr import bias_correction, parse_slice
from quicklook.tileinfo import ccds_by_name
from quicklook.types import AmpMeta, BBox, CcdId, ImageStat, PreProcessedCcd
from quicklook.utils.timeit import timeit
from quicklook.config import config

from .isr import parse_slice


def preprocess_ccd(
    ccd_id: CcdId,
    path: Path,
) -> PreProcessedCcd:
    match ccd_id.visit.data_type:
        case 'raw':
            return preprocess_ccd_raw(ccd_id, path)
        case 'calexp':
            return preprocess_ccd_calexp(ccd_id, path)
        case _:  # pragma: no cover
            raise ValueError(f'Unknown data_type: {ccd_id.visit.data_type}')


def preprocess_ccd_calexp(
    ccd_id: CcdId,
    path: Path,
) -> PreProcessedCcd:
    ccd_name = ccd_id.ccd_name
    with timeit(f'preprocess-{ccd_id.name}'):
        hdul= fast_open_comressed_fits(path)
        header = hdul[0].header  # type: ignore
        assert ccd_name == f'{header["RAFTNAME"]}_{header["SENSNAME"]}'
        bbox = ccds_by_name()[ccd_name].bbox
        pool: numpy.ndarray = hdul[1].data  # type: ignore
        with timeit(f'image-stat-{ccd_id.name}'):
            stat = image_stat(pool)
        return PreProcessedCcd(
            ccd_id=ccd_id,
            bbox=bbox,
            pool=pool,
            stat=stat,
            amps=[],
        )


@dataclass
class RawAmp:
    fits_index: int
    header: dict[str, Any]
    data: numpy.ndarray
    wcs: 'RawFitsWcs'

    @classmethod
    def from_hdu(cls, fits_index: int, hdu: afits.ImageHDU):
        header: dict[str, Any] = dict(hdu.header)  # type: ignore
        wcs = RawFitsWcs.from_header(header)
        datasec = parse_slice(header['DATASEC'])  # type: ignore
        raw: numpy.ndarray = hdu.data.copy()  # type: ignore
        corrected = bias_correction(raw, datasec=datasec)
        return cls(
            fits_index=fits_index,
            header=header,
            data=corrected,
            wcs=wcs,
        )


def preprocess_ccd_raw(
    ccd_id: CcdId,
    path: Path,
) -> PreProcessedCcd:
    ccd_name = ccd_id.ccd_name
    with timeit(f'preprocess-{ccd_id.name}'):
        hdul = fast_open_comressed_fits(path)
        header = hdul[0].header  # type: ignore
        assert ccd_name == f'{header["RAFTBAY"]}_{header["CCDSLOT"]}'
        amps = [RawAmp.from_hdu(j, hdu) for j, hdu in enumerate(hdul) if hdu.name.startswith('Segment')]  # type: ignore
        assembly = assemble_raw_amps(amps, ccd_name)
        with timeit(f'image-stat-{ccd_id.name}'):
            stat = image_stat(assembly.data)
        return PreProcessedCcd(
            ccd_id=ccd_id,
            bbox=assembly.bbox,
            pool=assembly.data,
            stat=stat,
            amps=assembly.amp_metas,
        )


def fast_open_comressed_fits(path: Path):
    buf = mineo_fits_decompress.decompressed_bytes(path, config.fitsio_decompress_parallel)
    return afits.HDUList.fromstring(buf)


@dataclass
class AssemblyResult:
    bbox: BBox
    data: numpy.ndarray
    amp_metas: list[AmpMeta]


def assemble_raw_amps(amps: Iterable[RawAmp], ccd_name: str) -> AssemblyResult:
    # bbox = functools.reduce(lambda a, b: a.union(b.wcs.bbox), amps[1:], amps[0].wcs.bbox)
    bbox = ccds_by_name()[ccd_name].bbox
    pool = numpy.zeros(
        (int(bbox.maxy - bbox.miny) + 1, int(bbox.maxx - bbox.minx) + 1),
        dtype=numpy.float32,
    )
    amp_metas: list[AmpMeta] = []
    for amp in amps:
        aligned = amp.wcs.align(amp.data)
        b = amp.wcs.bbox
        pool[
            int(b.miny - bbox.miny) : int(b.maxy - bbox.miny + 1),
            int(b.minx - bbox.minx) : int(b.maxx - bbox.minx + 1),
        ] = aligned
        amp_metas.append(
            AmpMeta(
                amp_id=amp.fits_index,
                bbox=b,
            )
        )
    return AssemblyResult(
        bbox=bbox,
        data=pool,
        amp_metas=amp_metas,
    )


def image_stat(array: numpy.ndarray):
    median: Any = numpy.median(array)
    mad: Any = numpy.median(numpy.absolute(array - median))
    return ImageStat(
        median=float(median),
        mad=float(mad),
        shape=array.shape,
    )


@dataclass
class RawFitsWcs:
    PC1_1: float
    PC1_2: float
    PC2_1: float
    PC2_2: float
    CRVAL1: float
    CRVAL2: float
    DATASEC: str

    @classmethod
    def from_header(cls, header, wcs_system='E'):
        d: Any = {
            'DATASEC': header['DATASEC'],
        }
        for f in 'PC1_1 PC1_2 PC2_1 PC2_2 CRVAL1 CRVAL2'.split():
            d[f] = float(header[f'{f}{wcs_system}'])
        return cls(**d)

    @functools.cached_property
    def data_section(self):
        return parse_slice(self.DATASEC)

    @functools.cached_property
    def pc(self):
        pc = numpy.array(
            [
                [self.PC1_1, self.PC1_2],
                [self.PC2_1, self.PC2_2],
            ]
        )
        return pc

    @functools.cached_property
    def corners(self):
        (x1, x2), (y1, y2) = self.data_section
        return numpy.array(
            [
                [x1, x2, x2, x1],
                [y1, y1, y2, y2],
            ]
        )

    @functools.cached_property
    def bbox(self):
        X, Y = ((self.pc @ self.corners).T + [self.CRVAL1, self.CRVAL2]).T
        return BBox(
            miny=Y.min(),
            maxy=Y.max(),
            minx=X.min(),
            maxx=X.max(),
        )

    def align(self, data: numpy.ndarray):
        assert abs(abs(numpy.linalg.det(self.pc)) - 1) < 1.0e-2
        ex, ey = self.pc.T
        if abs(ex[0]) < abs(ey[0]):  # pragma: no branch
            data = data.T
            ex, ey = ey, ex
        if ex[0] < 0:
            data = data[:, ::-1]
        if ey[1] < 0:  # pragma: no branch
            data = data[::-1]
        return data
