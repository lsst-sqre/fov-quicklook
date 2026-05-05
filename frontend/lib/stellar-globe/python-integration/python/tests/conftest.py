import pytest

from hscmap import Window
from hscmap.comm.mock import MockCommOptions


@pytest.fixture
def w():
    options = MockCommOptions(base_url="http://localhost:3000")
    return Window(comm_options=options)
