import math

from astropy.io import fits

from quicklook.utils.wcs import FitsWcsHeader, extract_display_wcs, fit_affine_wcs


def test_extract_display_wcs_converts_pc_and_cdelt_to_cd():
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 32
    header["NAXIS2"] = 16
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 10.0
    header["CRVAL2"] = 20.0
    header["CRPIX1"] = 5.0
    header["CRPIX2"] = 6.0
    header["PC1_1"] = 1.0
    header["PC1_2"] = 0.5
    header["PC2_1"] = 0.25
    header["PC2_2"] = 1.0
    header["CDELT1"] = -0.0001
    header["CDELT2"] = 0.0002

    assert extract_display_wcs(header) == FitsWcsHeader(
        NAXIS1=32,
        NAXIS2=16,
        CTYPE1="RA---TAN",
        CTYPE2="DEC--TAN",
        CRVAL1=10.0,
        CRVAL2=20.0,
        CRPIX1=5.0,
        CRPIX2=6.0,
        CD1_1=-0.0001,
        CD1_2=-0.00005,
        CD2_1=0.00005,
        CD2_2=0.0002,
    )


def test_extract_display_wcs_normalizes_tan_sip():
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 12
    header["NAXIS2"] = 8
    header["CTYPE1"] = "RA---TAN-SIP"
    header["CTYPE2"] = "DEC--TAN-SIP"
    header["CRVAL1"] = 30.0
    header["CRVAL2"] = -15.0
    header["CRPIX1"] = 2.0
    header["CRPIX2"] = 3.0
    header["CD1_1"] = -0.0002
    header["CD1_2"] = 0.0
    header["CD2_1"] = 0.0
    header["CD2_2"] = 0.0002

    sky_wcs = extract_display_wcs(header)

    assert sky_wcs is not None
    assert sky_wcs.CTYPE1 == "RA---TAN"
    assert sky_wcs.CTYPE2 == "DEC--TAN"


def test_extract_display_wcs_returns_none_without_celestial_wcs():
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 4
    header["NAXIS2"] = 4
    header["PC1_1E"] = 1.0
    header["PC2_2E"] = 1.0
    header["CRVAL1E"] = 0.0
    header["CRVAL2E"] = 0.0

    assert extract_display_wcs(header) is None


def test_fit_affine_wcs_builds_expected_header():
    wcs = fit_affine_wcs(
        width=10,
        height=20,
        sky_origin_deg=(10.0, 20.0),
        pixel_to_field_angle=lambda x, y: (
            1.0e-6 * x - 2.0e-3,
            -2.0e-6 * y + 3.0e-3,
        ),
    )

    assert wcs.NAXIS1 == 10
    assert wcs.NAXIS2 == 20
    assert wcs.CRVAL1 == 10.0
    assert wcs.CRVAL2 == 20.0
    assert math.isclose(wcs.CRPIX1, 2000.5)
    assert math.isclose(wcs.CRPIX2, 1500.5)
    assert math.isclose(wcs.CD1_1, math.degrees(1.0e-6))
    assert math.isclose(wcs.CD1_2, 0.0, abs_tol=1.0e-15)
    assert math.isclose(wcs.CD2_1, 0.0, abs_tol=1.0e-15)
    assert math.isclose(wcs.CD2_2, math.degrees(-2.0e-6))
