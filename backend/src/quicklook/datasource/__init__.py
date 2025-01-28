from functools import cache

from quicklook.config import config
from .types import DataSourceBase


@cache
def get_datasource() -> DataSourceBase:
    match config.data_source:
        case 'butler':
            from .butler_datasource import ButlerDataSource

            return ButlerDataSource()
        case 'dummy':
            from .dummy_datasource import DummyDataSource

            return DummyDataSource()
        case _:
            raise ValueError(f"Unknown datasource: {config.data_source}")
