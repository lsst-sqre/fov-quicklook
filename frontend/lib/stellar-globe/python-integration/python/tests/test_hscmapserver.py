from hscmap.comm.hscmapserver import HscmapServerCommOptions
from hscmap import Window
import pytest

pytestmark = [pytest.mark.skip]


def test_hscmapserver():
    options = HscmapServerCommOptions(backend_url='ws://localhost:3000', frontend_url='http://localhost:3000')
    w = Window(comm_options=options)

