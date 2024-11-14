from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from quicklook.config import config


def setup_static_assets(app: FastAPI):  # pragma: no cover
    assets_dir = Path(config.frontend_assets_dir)
    if assets_dir.exists():  # pragma: no cover
        mount_static_files(config.frontend_app_prefix, app, assets_dir)


def mount_static_files(prefix: str, app: FastAPI, path: Path):  # pragma: no cover
    # prefix: '' or '/fov-quicklook'

    for i, p in enumerate(path.glob('*')):
        if p.is_dir():
            app.mount(f"{prefix}/{p.name}", StaticFiles(directory=p))
        else:

            def f(q: Path):
                def g():
                    return FileResponse(str(q), headers={'Cache-Control': 'no-cache'} if q.name.endswith('.html') else {})

                g.__name__ = f'static_assets_{i}'
                return g

            if p.name == 'index.html':
                app.get(f"{prefix}/", operation_id=prefix)(f(p))
            else:
                app.get(f"{prefix}/{p.name}", operation_id=f"{prefix}{p.name}")(f(p))
