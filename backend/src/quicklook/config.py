from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
    )

    environment: Literal['production', 'test'] = 'production'

    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None

    # Communication settings
    frontend_port: int = 9500
    generator_port: int = 9502
    coordinator_base_url: str = 'http://localhost:9501'
    comm_heartbeat_interval: int = 10  # seconds
    comm_heartbeat_timeout: int = 2  # seconds
    comm_registration_interval: int = 10  # seconds
    comm_generator_max_concurrent_jobs: int = 4


config = Config()
