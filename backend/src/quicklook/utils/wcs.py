import math
import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import numpy
import starlink.Ast as Ast
from astropy.wcs import WCS


@dataclass
class FitsWcsHeader:
    NAXIS1: int
    NAXIS2: int
    CRVAL1: float
    CRVAL2: float
    CRPIX1: float
    CRPIX2: float
    CD1_1: float
    CD1_2: float
    CD2_1: float
    CD2_2: float
    CTYPE1: str = "RA---TAN"
    CTYPE2: str = "DEC--TAN"


def extract_display_wcs(header: Any) -> FitsWcsHeader | None:
    naxis1 = header.get("NAXIS1")
    naxis2 = header.get("NAXIS2")
    if not isinstance(naxis1, (int, float)) or not isinstance(naxis2, (int, float)):
        return None

    try:
        wcs = WCS(header, relax=True)
    except Exception:
        return None

    if not wcs.has_celestial:
        return None

    celestial = wcs.celestial
    if celestial.pixel_n_dim != 2 or celestial.world_n_dim != 2:
        return None

    ctype = celestial.wcs.ctype
    ctype1 = _normalize_tan_ctype(ctype[0] if len(ctype) > 0 else None, prefix="RA---")
    ctype2 = _normalize_tan_ctype(ctype[1] if len(ctype) > 1 else None, prefix="DEC--")
    if ctype1 is None or ctype2 is None:
        return None

    cd = numpy.asarray(celestial.pixel_scale_matrix, dtype=float)

    # ponytail: keep the browser payload to the linear TAN terms; add SIP
    # coefficients only if the displayed cursor coordinate needs that accuracy.
    return FitsWcsHeader(
        NAXIS1=int(naxis1),
        NAXIS2=int(naxis2),
        CTYPE1=ctype1,
        CTYPE2=ctype2,
        CRVAL1=float(celestial.wcs.crval[0]),
        CRVAL2=float(celestial.wcs.crval[1]),
        CRPIX1=float(celestial.wcs.crpix[0]),
        CRPIX2=float(celestial.wcs.crpix[1]),
        CD1_1=float(cd[0, 0]),
        CD1_2=float(cd[0, 1]),
        CD2_1=float(cd[1, 0]),
        CD2_2=float(cd[1, 1]),
    )


def fit_affine_wcs(
    *,
    width: int,
    height: int,
    sky_origin_deg: tuple[float, float],
    pixel_to_field_angle: Callable[[float, float], tuple[float, float]],
) -> FitsWcsHeader:
    samples = numpy.array([
        [0.5, 0.5],
        [width - 0.5, 0.5],
        [0.5, height - 0.5],
        [width - 0.5, height - 0.5],
        [width / 2.0, height / 2.0],
    ], dtype=float)

    design = numpy.column_stack([samples, numpy.ones(len(samples))])
    field_angles = numpy.array(
        [pixel_to_field_angle(float(x), float(y)) for x, y in samples],
        dtype=float,
    )

    coeffs, *_ = numpy.linalg.lstsq(design, field_angles, rcond=None)
    matrix = coeffs[:2, :].T
    offset = coeffs[2, :]
    crpix = 0.5 - numpy.linalg.solve(matrix, offset)

    return FitsWcsHeader(
        NAXIS1=width,
        NAXIS2=height,
        CRVAL1=sky_origin_deg[0],
        CRVAL2=sky_origin_deg[1],
        CRPIX1=float(crpix[0]),
        CRPIX2=float(crpix[1]),
        CD1_1=math.degrees(matrix[0, 0]),
        CD1_2=math.degrees(matrix[0, 1]),
        CD2_1=math.degrees(matrix[1, 0]),
        CD2_2=math.degrees(matrix[1, 1]),
    )


def extract_display_wcs_from_lsst_exposure(
    hdul: Sequence[Any],
    *,
    ccd_name: str,
) -> FitsWcsHeader | None:
    try:
        width = int(hdul[1].header["NAXIS1"])
        height = int(hdul[1].header["NAXIS2"])
        sky_origin_deg = _sky_origin_from_header(hdul[0].header)
        if sky_origin_deg is None:
            return None

        transform_rows = _find_hdu_by_name(hdul, "TransformMap").data
        if transform_rows is None:
            return None

        fp_to_field = None
        fp_to_pixels = None
        for row in transform_rows:
            from_name = _table_string(row["fromSysName"])
            from_detector = _table_string(row["fromSysDetectorName"])
            to_name = _table_string(row["toSysName"])
            to_detector = _table_string(row["toSysDetectorName"])

            if from_name == "FocalPlane" and to_name == "FieldAngle":
                fp_to_field = _read_transform(hdul, int(row["transform"]))
            elif (
                from_name == "FocalPlane"
                and to_name == "Pixels"
                and from_detector == ""
                and to_detector == ccd_name
            ):
                fp_to_pixels = _read_transform(hdul, int(row["transform"]))

            if fp_to_field is not None and fp_to_pixels is not None:
                break

        if fp_to_field is None or fp_to_pixels is None:
            return None

        return fit_affine_wcs(
            width=width,
            height=height,
            sky_origin_deg=sky_origin_deg,
            pixel_to_field_angle=lambda x, y: _pixel_to_field_angle(
                fp_to_pixels=fp_to_pixels,
                fp_to_field=fp_to_field,
                x=x,
                y=y,
            ),
        )
    except Exception:
        return None


def _pixel_to_field_angle(
    *,
    fp_to_pixels: Any,
    fp_to_field: Any,
    x: float,
    y: float,
) -> tuple[float, float]:
    focal = fp_to_pixels.tran([[x], [y]], False)
    field = fp_to_field.tran([[focal[0][0]], [focal[1][0]]], True)
    return float(field[0][0]), float(field[1][0])


def _read_transform(hdul: Sequence[Any], transform_id: int) -> Any:
    archive_index = _find_hdu_by_name(hdul, "ARCHIVE_INDEX").data
    if archive_index is None:
        raise ValueError("ARCHIVE_INDEX table is missing")

    for row in archive_index:
        if int(row["id"]) != transform_id:
            continue

        hdu_index = _archive_hdu_index(hdul, int(row["cat.archive"]))
        row0 = int(row["row0"])
        transform_bytes = bytes(hdul[hdu_index].data[row0][0])
        transform_text = transform_bytes.decode("utf-8", errors="replace")
        return _parse_ast_mapping(transform_text)

    raise KeyError(transform_id)


def _archive_hdu_index(hdul: Sequence[Any], archive_id: int) -> int:
    ar_hdu = int(hdul[0].header["AR_HDU"]) - 1
    return ar_hdu + archive_id


def _parse_ast_mapping(text: str) -> Any:
    text = re.sub(r"^\s*\d+\s+\w+\s+", "", text, count=1)
    mapping = Ast.Channel(_AstStringSource(text), None).read()
    if mapping is None:
        raise ValueError("Failed to parse AST mapping")
    return mapping


def _find_hdu_by_name(hdul: Sequence[Any], name: str) -> Any:
    for hdu in hdul:
        if getattr(hdu, "name", "") == name:
            return hdu
    raise KeyError(name)


def _table_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if hasattr(value, "tolist"):
        listed = value.tolist()
        if isinstance(listed, list):
            return "".join(str(item) for item in listed).strip()
    try:
        return "".join(str(item) for item in value).strip()
    except TypeError:
        return str(value).strip()


def _sky_origin_from_header(header: Any) -> tuple[float, float] | None:
    ra_start = _numeric_header_value(header, "RASTART")
    ra_end = _numeric_header_value(header, "RAEND")
    dec_start = _numeric_header_value(header, "DECSTART")
    dec_end = _numeric_header_value(header, "DECEND")
    if (
        ra_start is not None
        and ra_end is not None
        and dec_start is not None
        and dec_end is not None
    ):
        return (
            _mean_ra_degrees(ra_start, ra_end),
            (dec_start + dec_end) / 2.0,
        )

    ra = _numeric_header_value(header, "RA")
    dec = _numeric_header_value(header, "DEC")
    if ra is not None and dec is not None and not (float(ra) == 0.0 and float(dec) == 0.0):
        return float(ra), float(dec)

    return None


def _numeric_header_value(header: Any, key: str) -> float | None:
    value = header.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _mean_ra_degrees(a: float, b: float) -> float:
    sa = math.sin(math.radians(a)) + math.sin(math.radians(b))
    ca = math.cos(math.radians(a)) + math.cos(math.radians(b))
    return math.degrees(math.atan2(sa, ca)) % 360.0


def _normalize_tan_ctype(value: Any, *, prefix: str) -> str | None:
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    if value == f"{prefix}TAN" or value.startswith(f"{prefix}TAN-"):
        return f"{prefix}TAN"
    return None


class _AstStringSource:
    def __init__(self, text: str) -> None:
        self._lines: Iterator[str] = iter(text.splitlines())

    def astsource(self) -> str | None:
        return next(self._lines, None)
