from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='QUICKLOOK_',
        env_nested_delimiter='__',
        nested_model_default_partial_update=True,
        case_sensitive=True,
    )

    dev_reload: bool = False
    dev_log_prefix: str = ''
    dev_ccd_limit: int | None = None
    
    # Communication settings
    comm_heartbeat_interval: int = 30  # seconds
    comm_heartbeat_timeout: int = 10   # seconds
    comm_registration_interval: int = 60  # seconds
    comm_max_retries: int = 3
    comm_retry_delay: int = 5  # seconds


config = Config()
