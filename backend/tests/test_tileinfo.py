import pytest

from quicklook.tileinfo import TileInfo

# pytestmark = pytest.mark.focus


def test_tileinfo():
    ti = TileInfo.of(7, 0, 0)
    assert len([*ti.ccd_names]) == 59


def test_tileinfo_consistency():
    for _ in range(10000):
        assert set(TileInfo.of(6, 0, 1).ccd_names) == {
            'R02_S20',
            'R01_S01',
            'R02_S00',
            'R12_S01',
            'R01_S10',
            'R02_S10',
            'R01_S11',
            'R01_S21',
            'R02_S11',
            'R12_S00',
            'R01_S22',
            'R01_S12',
            'R11_S00',
            'R01_S00',
            'R02_S21',
            'R01_S02',
            'R02_S01',
            'R11_S01',
            'R01_S20',
            'R11_S02',
        }
