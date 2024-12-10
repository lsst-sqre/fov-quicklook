# This test is to confirm that the butler package is working properly.

import os
from pathlib import Path

import pytest

access_token_file = Path(__file__).parent / 'secrets' / 'butler_access_token'


@pytest.mark.skipif(not access_token_file.exists(), reason="No access token found")
def test_butler():
    from quicklook.utils.dummypyarrow import activate_dummy_pyarrow_when_non_x86_v2

    activate_dummy_pyarrow_when_non_x86_v2()
    
    from lsst.daf.butler import Butler

    os.environ['ACCESS_TOKEN'] = access_token_file.read_text().strip()
    butler = Butler(
        'https://data.lsst.cloud/api/butler/repo/dp02/butler.yaml',
        collections="2.2i/runs/DP0.2",
    )  # type: ignore
    instrument = 'LSSTCam-imSim'
    visit = 192350
    query = f"instrument='{instrument}' and visit={visit} and detector in (0..100:1)"
    data_type = 'calexp'
    refs = [*butler.registry.queryDatasets(data_type, where=query)]
    butler.getURI(refs[0])
