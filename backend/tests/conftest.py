import pickle
from pathlib import Path

import minio
import pytest

from quicklook.config import config
from quicklook.generator.preprocess_ccd import preprocess_ccd
from quicklook.types import CcdId, PreProcessedCcd, Visit
from quicklook.utils.s3 import download_object_from_s3

ccd_id = 'R01_S12'


@pytest.fixture(scope='session')
def broccoli_fits_and_ccd_id():
    cache_path = Path('./tmp/broccoli.fits')
    if not cache_path.exists():
        s3_config = config.s3_repository
        client = minio.Minio(
            s3_config.endpoint,
            access_key=s3_config.access_key,
            secret_key=s3_config.secret_key,
            secure=s3_config.secure,
        )
        file_contents = download_object_from_s3(client, s3_config.bucket, f'raw/broccoli/{ccd_id}.fits')
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open('wb') as f:
            f.write(file_contents)
    return cache_path, ccd_id


@pytest.fixture(scope='session')
def broccoli_fits(broccoli_fits_and_ccd_id: tuple[Path, str]) -> Path:
    return broccoli_fits_and_ccd_id[0]


@pytest.fixture(scope='session')
def preprocessed_ccd(broccoli_fits: Path) -> PreProcessedCcd:
    cache_path = Path('./tmp/preprocessed_ccd.pkl')

    if cache_path.exists():
        return pickle.loads(cache_path.read_bytes())

    visit = Visit.from_id('raw:broccoli')
    ppccd = preprocess_ccd(CcdId(visit, ccd_id), broccoli_fits)
    cache_path.write_bytes(pickle.dumps(ppccd))
    return ppccd
