import io

import astropy.io.fits as pyfits

from quicklook.frontend.api import get_fits_header
from quicklook.types import CcdDataRef, CcdName, VisitName
from quicklook.utils.s3 import NoSuchKey


async def test_get_fits_header_falls_back_to_datasource_when_cache_is_missing(monkeypatch):
    visit = VisitName('repo:LSSTCam!-raw!-all:raw:exposure=4242')
    ccd = CcdName('R22_S11')
    captured: dict[str, CcdDataRef] = {}

    async def fake_get_fits_header_from_object_storage(
        visit_name: VisitName,
        ccd_name: CcdName,
    ):
        assert visit_name == visit
        assert ccd_name == ccd
        raise NoSuchKey('missing')

    class FakeDataSource:
        async def get_data(self, ref: CcdDataRef) -> bytes:
            captured['ref'] = ref
            hdu = pyfits.PrimaryHDU()
            hdu.header['TESTKEY'] = 'VALUE'
            with io.BytesIO() as buf:
                pyfits.HDUList([hdu]).writeto(buf)
                return buf.getvalue()

    monkeypatch.setattr(get_fits_header, '_get_fits_header_from_object_storage', fake_get_fits_header_from_object_storage)
    monkeypatch.setattr(get_fits_header, 'get_datasource', lambda: FakeDataSource())

    headers = await get_fits_header._get_fits_header(visit, ccd)

    assert captured['ref'] == CcdDataRef(visit=visit, ccd=ccd)
    assert any(card[0] == 'TESTKEY' and card[2] == 'VALUE' for card in headers[0])
