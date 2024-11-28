import astropy.io.fits as pyfits

from quicklook.types import HeaderType


def fitsheader_to_list(hdul: pyfits.HDUList) -> list[HeaderType]:
    headers: list[HeaderType] = []
    for hdu in hdul:
        cards: HeaderType = []
        for card in hdu.header.cards:  # type: ignore
            keyword, value, comment = card
            cards.append((keyword, value.__class__.__name__, stringify(value), comment))
        headers.append(cards)
    return headers


def stringify(value) -> str:
    if isinstance(value, bool):
        return 'T' if value else 'F'
    return str(value)
