from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

from quicklook.config import config


class SPAStaticFiles:
    def __init__(self, directory: Path, html: bool = True):
        self.static_files = StaticFiles(directory=str(directory), html=html)
        self.directory = directory
        self.index_path = directory / "index.html"

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if not self.index_path.exists():
            raise RuntimeError("index.html not found")

        request = Request(scope, receive, send)
        path = request.url.path

        # APIリクエストはスキップ
        if path.startswith(f"{config.frontend_app_prefix}/api/"):
            return await self.static_files(scope, receive, send)

        try:
            # 静的ファイルが存在する場合はそれを返す
            return await self.static_files(scope, receive, send)
        except Exception:
            # 存在しない場合はindex.htmlを返す
            return await FileResponse(self.index_path)(scope, receive, send)


def setup_static_assets(app: FastAPI):  # pragma: no cover
    assets_dir = Path(config.frontend_assets_dir)
    if assets_dir.exists():
        app.mount(config.frontend_app_prefix, SPAStaticFiles(assets_dir))
