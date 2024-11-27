import json
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from . import app


def generate_openapi_json():
    # OpenAPI仕様を取得
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # JSONとして標準出力に出力
    print(json.dumps(openapi_schema, indent=4))


if __name__ == "__main__":
    generate_openapi_json()
