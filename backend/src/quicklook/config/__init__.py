import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from quicklook.datasets import get_dataset
from quicklook.types import build_scope_id
from quicklook.utils.s3 import S3Config


class ContextMenuTemplate(BaseModel):
    name: str
    template: str
    is_url: bool


class ButlerScopeConfig(BaseModel):
    """UI 上の検索プリセット。"""

    id: str | None = None
    dataset_type: str
    display_name: str
    collection: str
    repository_name: str = "embargo"
    instrument: str = "LSSTCam"

    @model_validator(mode='before')
    @classmethod
    def normalize_legacy_fields(cls, data):
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if 'dataset_type' not in normalized and 'data_type' in normalized:
            normalized['dataset_type'] = normalized.pop('data_type')
        if 'collection' not in normalized and 'collections' in normalized:
            collections = normalized.pop('collections')
            if isinstance(collections, list) and collections:
                normalized['collection'] = collections[0]
        return normalized

    @model_validator(mode='after')
    def set_scope_id(self):
        self.id = build_scope_id(self.repository_name, self.collection, self.dataset_type)
        return self

    @property
    def data_type(self) -> str:
        return self.dataset_type


DEFAULT_BUTLER_SCOPES = [
    ButlerScopeConfig(
        dataset_type='raw',
        display_name='Raw',
        collection='LSSTCam/raw/all',
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    ButlerScopeConfig(
        dataset_type='post_isr_image',
        display_name='Post-ISR',
        collection='LSSTCam/runs/nightlyValidation',
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    ButlerScopeConfig(
        dataset_type='difference_image',
        display_name='Difference Image',
        collection='LSSTCam/runs/nightlyValidation',
        repository_name='embargo',
        instrument='LSSTCam',
    ),
    ButlerScopeConfig(
        dataset_type='preliminary_visit_image',
        display_name='Preliminary',
        collection='LSSTCam/runs/nightlyValidation',
        repository_name='embargo',
        instrument='LSSTCam',
    ),
]
DEFAULT_BUTLER_SCOPE_REPOSITORIES = {
    scope.repository_name for scope in DEFAULT_BUTLER_SCOPES
}


def _copy_default_butler_scopes() -> list[ButlerScopeConfig]:
    return [scope.model_copy(deep=True) for scope in DEFAULT_BUTLER_SCOPES]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
        extra='ignore',
    )

    frontend_app_prefix: str = '/fov-quicklook'
    context_menu_templates: list[ContextMenuTemplate] = []
    admin_page: bool = False

    environment: Literal['production', 'development', 'test'] = 'production'

    tile_size: int = 256
    tile_max_level: int = 8
    tile_pack: int = 2
    tile_cache_schema_version: int = 2
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
    query_builder_input_mode: Literal['select', 'combobox'] = 'combobox'

    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'
    comm_heartbeat_interval: int = 5
    comm_heartbeat_timeout: int = 2
    comm_registration_interval: int = 10
    comm_use_coordinator_service_host: bool = False
    comm_force_ipv4_internal: bool = False
    rpc_timeout_total: float = 600
    rpc_open_timeout: float = 10
    rpc_close_timeout: float = 5
    rpc_ping_interval: float = 5
    rpc_ping_timeout: float = 10
    rpc_process_pool_workers: int = 4

    http_client_connection_limit: int = 100
    http_client_dns_cache_ttl: int = 300
    http_client_keepalive_timeout: int = 30

    generator_max_concurrent_jobs: int = 4
    generator_max_concurrent_ccds_per_job: int = 10
    merge_tile_parallel: int = 4
    transfer_tile_parallel: int = 4

    resubmit_min_age_seconds: float = 10.0
    resubmit_max_attempts_per_ccd: int = 3
    ccd_queue_timeout_seconds: float = 60.0
    generate_single_fits_tiles_timeout_seconds: float = 300.0

    pipeline_queue_size: int = 64
    pipeline_generate_single_fits_tiles: int = 1
    pipeline_transfer_queue_size: int = 8
    pipeline_merge_tiles: int = 1
    pipeline_transfer_tiles: int = 2

    log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'
    timeit_log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'debug'

    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None
    dev_generator_required_coordinator_connection: bool = True

    db_url: str = 'postgresql+asyncpg://quicklook:quicklook@localhost:5432/quicklook'

    max_object_storage_usage: int = 1024 * 1024 * 1024 * 45
    housekeeping_keep_recent_count: int = 10

    pipeline_stage_timeout: int = 600

    ccd_data_types: list[dict[str, object]] | None = Field(default=None, exclude=True)
    butler_scopes: list[ButlerScopeConfig] = Field(default_factory=_copy_default_butler_scopes)
    configured_butler_scope_keys: set[tuple[str, str, str]] = Field(default_factory=set, exclude=True)

    @model_validator(mode='before')
    @classmethod
    def normalize_butler_scope_config(cls, data):
        if not isinstance(data, dict):
            return data
        configured = data.get('butler_scopes')
        if configured is None and isinstance(data.get('ccd_data_types'), list):
            converted = []
            for item in data['ccd_data_types']:
                if not isinstance(item, dict):
                    continue
                collections = item.get('collections')
                if isinstance(collections, list) and collections:
                    for collection in collections:
                        converted.append({
                            'dataset_type': item.get('dataset_type', item.get('data_type')),
                            'display_name': item.get('display_name'),
                            'collection': collection,
                            'repository_name': item.get('repository_name', 'embargo'),
                            'instrument': item.get('instrument', 'LSSTCam'),
                        })
                else:
                    converted.append(item)
            configured = converted
        if not isinstance(configured, list):
            return data

        configured_keys = set()
        for item in configured:
            if not isinstance(item, dict):
                continue
            dataset_type = item.get('dataset_type', item.get('data_type'))
            collection = item.get('collection')
            if collection is None and isinstance(item.get('collections'), list) and item['collections']:
                collection = item['collections'][0]
            if not isinstance(dataset_type, str) or not dataset_type:
                continue
            if not isinstance(collection, str) or not collection:
                continue
            repository_name = item.get('repository_name', 'embargo')
            if not isinstance(repository_name, str) or not repository_name:
                repository_name = 'embargo'
            configured_keys.add((repository_name, collection, dataset_type))

        merged = dict(data)
        merged['butler_scopes'] = configured
        merged['configured_butler_scope_keys'] = configured_keys
        return merged

    @model_validator(mode='after')
    def merge_missing_default_butler_scopes(self):
        configured_by_key = {
            (scope.repository_name, scope.collection, scope.dataset_type): scope
            for scope in self.butler_scopes
        }
        configured_default_repositories = {
            scope.repository_name
            for scope in self.butler_scopes
            if scope.repository_name in DEFAULT_BUTLER_SCOPE_REPOSITORIES
        }

        if not configured_default_repositories:
            return self

        merged = []
        for default in DEFAULT_BUTLER_SCOPES:
            if default.repository_name not in configured_default_repositories:
                continue
            key = (default.repository_name, default.collection, default.dataset_type)
            merged.append(configured_by_key.pop(key, default.model_copy(deep=True)))
        merged.extend(configured_by_key.values())
        self.butler_scopes = merged
        return self

    @property
    def system_info_butler_scopes(self) -> list[ButlerScopeConfig]:
        if not self.configured_butler_scope_keys:
            return self.butler_scopes
        return [
            scope
            for scope in self.butler_scopes
            if (scope.repository_name, scope.collection, scope.dataset_type) in self.configured_butler_scope_keys
        ]

    @property
    def datasets(self) -> list[dict[str, object]]:
        dataset_types = {scope.dataset_type for scope in self.butler_scopes}
        return [get_dataset(dataset_type).model_dump() for dataset_type in sorted(dataset_types)]


config = Config(
    _env_file=os.environ.get('ENV_FILE'),  # type: ignore
)
