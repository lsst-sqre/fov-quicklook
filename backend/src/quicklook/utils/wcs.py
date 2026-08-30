from dataclasses import dataclass
from typing import Any

import numpy
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


def _normalize_tan_ctype(value: Any, *, prefix: str) -> str | None:
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    if value == f"{prefix}TAN" or value.startswith(f"{prefix}TAN-"):
        return f"{prefix}TAN"
    return None
