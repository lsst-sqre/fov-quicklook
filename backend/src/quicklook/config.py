from pprint import pprint
import os
import re
from functools import cached_property
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from quicklook.utils.s3 import S3Config

os.environ['http_proxy'] = ''


class Config(BaseSettings):
    environment: Literal['production', 'test'] = 'production'
    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'

    frontend_app_prefix: str = ''

    data_source: Literal['butler', 'dummy'] = 'butler'
    admin_page: bool = False

    @field_validator('frontend_app_prefix')
    def check_frontend_app_prefix(cls, value: str):
        if len(value) > 0:  # pragma: no cover
            if not value.startswith('/'):
                raise ValueError('frontend_app_prefix must start with /')
        return value

    frontend_assets_dir: str = './frontend-assets'

    s3_test_data: S3Config = S3Config(
        endpoint='localhost:9000',
        access_key='???',
        secret_key='???',
        secure=False,
        bucket='quicklook-test-data',
    )

    s3_tile: S3Config = S3Config(
        endpoint='localhost:9000',
        access_key='???',
        secret_key='???',
        secure=False,
        bucket='quicklook-tile',
    )

    tile_size: int = 256
    tile_max_level: int = 8
    tile_ccd_processing_parallel: int = 32
    tile_compression_level: int = 9
    tile_merge_parallel: int = 8

    tile_tmpdir: str = '/dev/shm/quicklook/tile_tmp'  # used in generator
    tile_merged_dir: str = '/tmp/quicklook/merged'  # used in generator
    fits_header_tmpdir: str = '/dev/shm/quicklook/fits_header'  # used in generator

    fitsio_tmpdir: str = '/dev/shm/quicklook/fitsio'  # used in generator
    fitsio_decompress_parallel: int = 4

    job_max_ram_limit_stage: int = 4
    job_max_disk_limit_stage: int = 20

    timeit_log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'

    db_url: str = 'postgresql://quicklook:quicklook@localhost:5432/quicklook'

    heartbeat_interval: float = 10

    @cached_property
    def coordinator_port(self) -> int:
        return int(self.coordinator_base_url.split(':')[-1])

    @cached_property
    def coordinator_ws_base_url(self) -> str:
        return re.sub(r'^http://', 'ws://', self.coordinator_base_url)

    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
    )

    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None


config = Config()


def main():  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='*', default=['.'])
    args = parser.parse_args()
    focus = config

    for target in args.path:
        route = target.split('.')
        for r in route:
            if r != '':
                focus = getattr(focus, r)
        pprint(focus)


if __name__ == '__main__':  # pragma: no cover
    main()
