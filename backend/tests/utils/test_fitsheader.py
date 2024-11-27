from pathlib import Path

import astropy.io.fits as pyfits
from pydantic import RootModel

from quicklook.utils import fitsheader

type CardType = tuple[str, str, str, str]
type HeaderType = list[CardType]


FitsHeader = RootModel[list[HeaderType]]


def test_fitsheader_to_list(broccoli_fits: Path):
    with pyfits.open(broccoli_fits) as hdul:
        raw = fitsheader.fitsheader_to_list(hdul)
        FitsHeader.model_validate(raw)
