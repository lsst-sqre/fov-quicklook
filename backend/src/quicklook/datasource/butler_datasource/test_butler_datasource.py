from quicklook.datasource.butler_datasource import Instrument


def test_instruments():
    i = Instrument.get('LSSTComCam')
    assert i.name == 'LSSTComCam'
    assert i.detector_2_ccd[0] == 'R22_S00'
    assert i.ccd_2_detector['R22_S00'] == 0
    assert i.detector_2_ccd[8] == 'R22_S22'
    assert i.ccd_2_detector['R22_S22'] == 8
