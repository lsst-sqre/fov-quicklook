from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from quicklook.config import config


def setup_static_assets(app: FastAPI):  # pragma: no cover
    assets_dir = Path(config.frontend_assets_dir)
    if assets_dir.exists():  # pragma: no cover
        mount_static_files(config.frontend_app_prefix, app, assets_dir)


def mount_static_files(prefix: str, app: FastAPI, path: Path):  # pragma: no cover
    # prefix: '' or '/fov-quicklook'
    app.mount(f"{prefix}", StaticFiles(directory=path, html=True))
