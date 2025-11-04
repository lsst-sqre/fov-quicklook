from quicklook.datasource.butler_datasource import Instrument
from quicklook.types import CcdName


def test_instruments():
    i = Instrument.get('LSSTComCam')
    assert i.name == 'LSSTComCam'
    assert i.detector_2_ccd[0] == 'R22_S00'
    assert i.ccd_2_detector[CcdName('R22_S00')] == 0
    assert i.detector_2_ccd[8] == 'R22_S22'
    assert i.ccd_2_detector[CcdName('R22_S22')] == 8
