import numpy

from quicklook.frontend.api import get_tile
from quicklook.types import TilePos, VisitName
from quicklook.utils import zstd
from quicklook.utils.numpyutils import npybytes2ndarray


async def test_get_tile_from_object_storage_returns_blank_tile_for_missing_entry(monkeypatch):
    class FakeStorage:
        def __init__(self, visit):
            self.visit = visit

        async def get_quicklook_tile_bytes(self, pos):
            del pos
            return None

    monkeypatch.setattr(get_tile, 'VisitObjectStorage', FakeStorage)

    response = await get_tile._get_tile_from_object_storage(VisitName('repo:raw:4242'), TilePos(level=7, i=0, j=1))

    assert response.media_type == 'application/npy+zstd'
    arr = npybytes2ndarray(zstd.decompress(response.body))
    assert arr.shape == (256, 256, 2)
    assert arr.dtype == numpy.float32
    assert numpy.count_nonzero(arr) == 0
