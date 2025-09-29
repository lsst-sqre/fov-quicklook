from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from quicklook.utils.s3 import S3Config


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
    )

    environment: Literal['production', 'test'] = 'production'

    tile_size: int = 256
    tile_max_level: int = 8
    tile_pack: int = 2  # (1<<tile_pack) ** 2 個のタイルがまとめてオブジェクトストレージにアップロードされる。
    # 例えばtile_pack==2のときは、16個のタイルがまとめてアップロードされる。

    fitsio_decompress_parallel: int = 4
    fitsio_tmpdir: Path = Path('/dev/shm/quicklook/fitsio')

    data_source: Literal['butler', 'dummy'] = 'butler'

    job_local_dir: Path = Path('/tmp/quicklook/jobs')

    s3_tile: S3Config = S3Config(
        endpoint='localhost:9000',
        access_key='???',
        secret_key='???',
        secure=False,
        bucket='quicklook-tile',
    )
    s3_tile_key_prefix: str = ''

    s3_test_data: S3Config = S3Config(
        endpoint='localhost:9000',
        access_key='???',
        secret_key='???',
        secure=False,
        bucket='quicklook-test-data',
    )

    # Communication settings
    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'
    comm_heartbeat_interval: int = 10  # seconds
    comm_heartbeat_timeout: int = 2  # seconds
    comm_registration_interval: int = 10  # seconds
    rpc_timeout_total: float = 600  # seconds

    max_job: int = 64
    generator_max_concurrent_jobs: int = 8
    merge_tile_parallel: int = 8
    transfer_tile_parallel: int = 8

    # Logging settings
    log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'
    timeit_log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'debug'

    # Development settings
    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None


config = Config()
