from dataclasses import dataclass
from pathlib import Path

import minio
import pytest

from quicklook.config import config
from quicklook.utils.s3 import download_object_from_s3


@pytest.fixture
def example_ccd():
    path = Path('example/broccoli_R01_S12.fits')

    if not path.exists():
        s3_config = config.s3_repository
        client = minio.Minio(
            s3_config.endpoint[0],
            access_key=s3_config.access_key,
            secret_key=s3_config.secret,
            secure=s3_config.secure,
        )
        file_contents = download_object_from_s3(client, s3_config.bucket, f'raw/broccoli/R01_S12.fits')
        path.write_bytes(file_contents)

    return path, 'R01_S12'
