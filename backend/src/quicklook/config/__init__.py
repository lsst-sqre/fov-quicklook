import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from quicklook.utils.s3 import S3Config


class ContextMenuTemplate(BaseModel):
    name: str
    template: str
    is_url: bool


class CcdDataTypeConfig(BaseModel):
    """CCDデータタイプの設定"""
    data_type: str  # Butler dataset type name (例: 'raw', 'calexp')
    display_name: str  # UI表示名 (例: 'Raw', 'Post-ISR')
    collections: list[str]  # Butlerコレクション名
    data_id_dimension: str = "exposure"  # Butlerでのデータ識別ディメンション ('exposure' or 'visit')
    order_by: list[str] = ["-exposure"]  # クエリの並び順
    partial: bool = False  # 部分読み込みを使用するか
    repository_name: str = "embargo"  # Butler リポジトリ名
    instrument: str = "LSSTCam"  # Butler instrument名


DEFAULT_CCD_DATA_TYPES = [
    CcdDataTypeConfig(
        data_type='raw',
        display_name='Raw',
        collections=['LSSTCam/raw/all'],
        data_id_dimension='exposure',
        order_by=['-day_obs', '-exposure'],
        partial=False,
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    CcdDataTypeConfig(
        data_type='post_isr_image',
        display_name='Post-ISR',
        collections=['LSSTCam/runs/nightlyValidation'],
        data_id_dimension='exposure',
        order_by=['-exposure'],
        partial=True,
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    CcdDataTypeConfig(
        data_type='difference_image',
        display_name='Difference Image',
        collections=['LSSTCam/runs/nightlyValidation'],
        data_id_dimension='visit',
        order_by=['-visit'],
        partial=True,
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    CcdDataTypeConfig(
        data_type='preliminary_visit_image',
        display_name='Preliminary',
        collections=['LSSTCam/runs/nightlyValidation'],
        data_id_dimension='visit',
        order_by=['-visit'],
        partial=True,
        repository_name='embargo',
        instrument='LSSTCam',
    ),
]
DEFAULT_CCD_DATA_TYPE_REPOSITORIES = {
    data_type.repository_name for data_type in DEFAULT_CCD_DATA_TYPES
}


def _copy_default_ccd_data_types() -> list[CcdDataTypeConfig]:
    return [data_type.model_copy(deep=True) for data_type in DEFAULT_CCD_DATA_TYPES]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
        extra='ignore',
    )

    # app settings
    frontend_app_prefix: str = '/fov-quicklook'
    context_menu_templates: list[ContextMenuTemplate] = []
    admin_page: bool = False

    environment: Literal['production', 'development', 'test'] = 'production'

    tile_size: int = 256
    tile_max_level: int = 8
    tile_pack: int = 2  # (1<<tile_pack) ** 2 個のタイルがまとめてオブジェクトストレージにアップロードされる。
    # 例えばtile_pack==2のときは、16個のタイルがまとめてアップロードされる。
    fitsio_decompress_parallel: int = 4
    fitsio_tmpdir: Path = Path('/tmp/quicklook/fitsio')
    fitsio_memory_saving_mode: bool = True

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

    frontend_assets_dir: str = './frontend-assets'

    # Communication settings
    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'
    comm_heartbeat_interval: int = 5  # seconds
    comm_heartbeat_timeout: int = 2  # seconds
    comm_registration_interval: int = 10  # seconds
    rpc_timeout_total: float = 600  # seconds
    rpc_open_timeout: float = 10  # seconds - timeout for WebSocket connection establishment
    rpc_close_timeout: float = 5  # seconds - timeout for WebSocket close handshake
    rpc_ping_interval: float = 5  # seconds - interval for WebSocket ping frames
    rpc_ping_timeout: float = 10  # seconds - timeout for WebSocket pong response
    rpc_process_pool_workers: int = 4

    # HTTP client settings (aiohttp.TCPConnector)
    http_client_connection_limit: int = 100
    http_client_dns_cache_ttl: int = 300  # seconds
    http_client_keepalive_timeout: int = 30  # seconds

    # Job settings
    generator_max_concurrent_jobs: int = 4
    generator_max_concurrent_ccds_per_job: int = 10 # ~1.6GB per generator; reduced from 25 to prevent OOMKill cascades
    merge_tile_parallel: int = 4
    transfer_tile_parallel: int = 4

    # CCD resubmit settings (for slow generator mitigation)
    resubmit_min_age_seconds: float = 10.0
    resubmit_max_attempts_per_ccd: int = 3   # Maximum resubmit attempts per CCD (0 to disable resubmit)
    ccd_queue_timeout_seconds: float = 60.0  # Timeout for Generator-side queue.get() to detect connection loss (1 minute)
    generate_single_fits_tiles_timeout_seconds: float = 120.0  # Timeout for entire CCD processing phase

    # Pipeline settings
    pipeline_queue_size: int = 64
    pipeline_generate_single_fits_tiles: int = 1
    pipeline_transfer_queue_size: int = 8
    pipeline_merge_tiles: int = 1
    pipeline_transfer_tiles: int = 2

    # Logging settings
    log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'
    timeit_log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'debug'

    # Development settings
    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None
    dev_generator_required_coordinator_connection: bool = True

    # Database settings
    db_url: str = 'postgresql+asyncpg://quicklook:quicklook@localhost:5432/quicklook'

    # Housekeeping settings
    max_object_storage_usage: int = 1024 * 1024 * 1024 * 45  # 45GB in bytes
    housekeeping_keep_recent_count: int = 10  # 最近作成されたquicklookをこの数だけ保持（アクセス頻度に関係なく）

    # Pipeline stage timeout settings (in seconds)
    pipeline_stage_timeout: int = 600  # 10 minutes; merge_tiles can be slow with concurrent jobs

    # CCD Data Types configuration
    ccd_data_types: list[CcdDataTypeConfig] = Field(default_factory=_copy_default_ccd_data_types)
    configured_ccd_data_type_keys: set[tuple[str, str]] = Field(default_factory=set, exclude=True)

    @model_validator(mode='before')
    @classmethod
    def capture_configured_ccd_data_type_keys(cls, data):
        if not isinstance(data, dict):
            return data

        configured = data.get('ccd_data_types')
        if not isinstance(configured, list):
            return data

        configured_keys = set()
        for item in configured:
            if not isinstance(item, dict):
                continue
            data_type = item.get('data_type')
            if not isinstance(data_type, str) or not data_type:
                continue
            repository_name = item.get('repository_name', 'embargo')
            if not isinstance(repository_name, str) or not repository_name:
                repository_name = 'embargo'
            configured_keys.add((repository_name, data_type))

        merged = dict(data)
        merged['configured_ccd_data_type_keys'] = configured_keys
        return merged

    @model_validator(mode='after')
    def merge_missing_default_ccd_data_types(self):
        configured_by_key = {
            (data_type.repository_name, data_type.data_type): data_type
            for data_type in self.ccd_data_types
        }
        configured_default_repositories = {
            data_type.repository_name
            for data_type in self.ccd_data_types
            if data_type.repository_name in DEFAULT_CCD_DATA_TYPE_REPOSITORIES
        }

        if not configured_default_repositories:
            return self

        merged = []
        for default in DEFAULT_CCD_DATA_TYPES:
            if default.repository_name not in configured_default_repositories:
                continue
            key = (default.repository_name, default.data_type)
            merged.append(configured_by_key.pop(key, default.model_copy(deep=True)))
        merged.extend(configured_by_key.values())
        self.ccd_data_types = merged
        return self

    @property
    def system_info_ccd_data_types(self) -> list[CcdDataTypeConfig]:
        if not self.configured_ccd_data_type_keys:
            return self.ccd_data_types
        return [
            data_type
            for data_type in self.ccd_data_types
            if (data_type.repository_name, data_type.data_type) in self.configured_ccd_data_type_keys
        ]


config = Config(
    _env_file=os.environ.get('ENV_FILE'),  # type: ignore
)
