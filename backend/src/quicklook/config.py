import re
from functools import cached_property
import os
from typing import Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

os.environ['http_proxy'] = ''


class S3Config(BaseModel):
    endpoint: list[str]
    access_key: str
    secret: str
    secure: bool
    bucket: str


class Config(BaseSettings):
    environment: Literal['production', 'test'] = 'production'
    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'

    s3_repository: S3Config = S3Config(
        endpoint=['localhost:9000'],
        access_key='???',
        secret='???',
        secure=False,
        bucket='quicklook-repository',
    )

    s3_tile: S3Config = S3Config(
        endpoint=['localhost:9000'],
        access_key='???',
        secret='???',
        secure=False,
        bucket='quicklook-tile',
    )

    tile_size: int = 256
    tile_max_level: int = 8
    tile_ccd_processing_parallel: int = 25
    tile_compression_level: int = 9
    tile_compression_parallel: int = 8
    tile_tmpdir: str = '/dev/shm/quicklook/tile_tmp'

    fitsio_tmpdir: str = '/dev/shm/quicklook/fitsio'
    fitsio_decompress_parallel: int = 4

    timeit_log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'

    db_url: str = 'postgresql://quicklook:quicklook@localhost:5432/quicklook'

    coordinator_work_dir: str = '/dev/shm/quicklook/coordinator'

    heartbeat_interval: float = 10

    @cached_property
    def coordinator_port(self) -> int:
        return int(self.coordinator_base_url.split(':')[-1])

    @cached_property
    def coordinator_ws_base_url(self) -> str:
        return re.sub(r'^http://', 'ws://', self.coordinator_base_url)

    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        case_sensitive=True,
    )

    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None


config = Config()
