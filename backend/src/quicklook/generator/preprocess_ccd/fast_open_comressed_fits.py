from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from math import prod
from pathlib import Path
from typing import Any, ClassVar

import numpy
from astropy.io.fits import Card

import mineo_fits_decompress

from quicklook.config import config


CARD_SIZE = 80
BLOCK_SIZE = 2880


@dataclass(frozen=True)
class CardProxy:
    keyword: str
    value: Any
    comment: str | None

    def __iter__(self) -> Iterator[Any]:
        yield self.keyword
        yield self.value
        yield self.comment or ''


class FitsHeader(Mapping[str, Any]):
    def __init__(self, cards: Iterable[Card]):
        stored_cards: list[CardProxy] = []
        mapping: dict[str, Any] = {}
        for card in cards:
            if card.keyword == 'END':
                continue
            proxy = CardProxy(card.keyword, card.value, card.comment)  # type: ignore
            stored_cards.append(proxy)
            if card.keyword in {'END', ''}:
                continue
            mapping[card.keyword] = card.value  # type: ignore
        self._cards = tuple(stored_cards)
        self._mapping = mapping

    def __getitem__(self, key: str) -> Any:
        return self._mapping[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)

    def get(self, key: str, default: Any = None) -> Any:
        return self._mapping.get(key, default)

    @property
    def cards(self) -> tuple[CardProxy, ...]:
        return self._cards


@dataclass(frozen=True)
class DataSpec:
    view: memoryview
    dtype: numpy.dtype[Any]
    shape: tuple[int, ...]
    bscale: float
    bzero: float

    @property
    def needs_scaling(self) -> bool:
        return not (self.bscale == 1 and self.bzero == 0)


class FastHdu:
    __slots__ = ('name', '_cards', '_data_spec', '_header', '_data')

    def __init__(self, name: str, cards: Sequence[Card], data_spec: DataSpec | None):
        self.name = name
        self._cards: tuple[Card, ...] = tuple(cards)
        self._data_spec = data_spec
        self._header: FitsHeader | None = None
        self._data: numpy.ndarray | None = None

    @property
    def header(self) -> FitsHeader:
        if self._header is None:
            self._header = FitsHeader(self._cards)
        return self._header

    @property
    def data(self) -> numpy.ndarray | None:
        spec = self._data_spec
        if spec is None:
            return None
        if self._data is None:
            array = numpy.frombuffer(spec.view, dtype=spec.dtype)
            if spec.shape:
                array = array.reshape(spec.shape)
            if spec.needs_scaling:
                array = numpy.asarray(array, dtype=numpy.float32) * float(spec.bscale) + float(spec.bzero)
            self._data = array
        return self._data


class FastHDUList(Sequence[FastHdu]):
    def __init__(self, buffer: bytes, hdus: list[FastHdu]):
        self._buffer = buffer
        self._hdus = hdus

    def __getitem__(self, index: int | slice) -> FastHdu | list[FastHdu]:
        return self._hdus[index]

    def __len__(self) -> int:
        return len(self._hdus)

    def __iter__(self) -> Iterator[FastHdu]:
        return iter(self._hdus)


class FitsParser:
    _dtype_map: ClassVar[dict[int, str]] = {
        8: '>u1',
        16: '>i2',
        32: '>i4',
        64: '>i8',
        -32: '>f4',
        -64: '>f8',
    }

    def __init__(self, buffer: bytes):
        self._buffer = buffer
        self._view = memoryview(buffer)
        self._offset = 0

    def parse(self) -> FastHDUList:
        hdus: list[FastHdu] = []
        while self._offset < len(self._buffer):
            header_cards, header_dict = self._read_header()
            if header_dict is None:
                break
            data_spec = self._read_data(header_dict)
            name = self._resolve_name(header_dict)
            hdus.append(FastHdu(name=name, cards=header_cards, data_spec=data_spec))
        return FastHDUList(self._buffer, hdus)

    def _read_header(self) -> tuple[list[Card], dict[str, Any] | None]:
        if self._offset >= len(self._buffer):
            return [], None
        header_cards: list[Card] = []
        end_found = False
        while not end_found:
            block = self._view[self._offset : self._offset + BLOCK_SIZE]
            if len(block) < BLOCK_SIZE:
                break
            for idx in range(0, BLOCK_SIZE, CARD_SIZE):
                raw_card = block[idx : idx + CARD_SIZE]
                card_text = raw_card.tobytes().decode('ascii')
                card = Card.fromstring(card_text)
                header_cards.append(card)
                if card.keyword == 'END':
                    end_found = True
                    break
            self._offset += BLOCK_SIZE
        if not end_found:
            return header_cards, None
        header_mapping = self._build_header_mapping(header_cards)
        return header_cards, header_mapping

    def _build_header_mapping(self, cards: Iterable[Card]) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        for card in cards:
            if card.keyword in {'END', '', 'COMMENT', 'HISTORY'}:
                continue
            mapping[card.keyword] = card.value  # type: ignore
        return mapping

    def _read_data(self, header: Mapping[str, Any]) -> DataSpec | None:
        bitpix = int(header.get('BITPIX', 0))
        naxis = int(header.get('NAXIS', 0))
        if naxis == 0 or bitpix == 0:
            return None
        axes = [int(header[f'NAXIS{i}']) for i in range(1, naxis + 1)]
        nelem = prod(axes)
        pcount = int(header.get('PCOUNT', 0))
        gcount = int(header.get('GCOUNT', 1))
        dtype_code = self._dtype_map.get(bitpix)
        if dtype_code is None:
            raise ValueError(f'Unsupported BITPIX {bitpix}')
        elem_size = numpy.dtype(dtype_code).itemsize
        pixel_bytes = nelem * gcount * elem_size
        raw_bytes = pcount + pixel_bytes
        data_start = self._offset
        data_end = data_start + pixel_bytes
        raw_end = data_start + raw_bytes
        data_view = self._view[data_start:data_end]
        self._offset = raw_end + (-raw_bytes % BLOCK_SIZE)

        xtension = str(header.get('XTENSION', '')).strip().upper()
        if xtension in {'BINTABLE', 'TABLE'}:
            return None

        dtype = numpy.dtype(dtype_code)
        shape: tuple[int, ...] = ()
        if nelem * gcount > 0:
            shape = tuple(int(header[f'NAXIS{i}']) for i in range(naxis, 0, -1))
            if gcount > 1:
                shape = (gcount,) + shape
        bscale = float(header.get('BSCALE', 1))
        bzero = float(header.get('BZERO', 0))
        return DataSpec(
            view=data_view,
            dtype=dtype,
            shape=shape,
            bscale=bscale,
            bzero=bzero,
        )

    def _resolve_name(self, header: Mapping[str, Any]) -> str:
        if 'EXTNAME' in header:
            return str(header['EXTNAME'])
        if header.get('SIMPLE') is True:
            return 'PRIMARY'
        xtension = header.get('XTENSION')
        if xtension:
            return str(xtension)
        return f'HDU{len(header)}'


def fast_open_comressed_fits(path: Path) -> FastHDUList:
    buf = mineo_fits_decompress.decompressed_bytes(path, config.fitsio_decompress_parallel)
    # import astropy.io.fits as pyfits
    # return pyfits.HDUList.fromstring(buf)
    parser = FitsParser(buf)
    return parser.parse()
