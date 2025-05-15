# testcode: test_hips.py
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from .filestore import hips_file, hips_repositories

logger = logging.getLogger(f'uvicorn.{__name__}')

router = APIRouter()


class HipsRepository(BaseModel):
    name: str


@router.get('/api/hips', response_model=list[HipsRepository])
def list_hips_repositories():
    return [HipsRepository(name=repo) for repo in hips_repositories()]


def validate_path(path: str) -> str:
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith("..") or normalized_path.startswith("/") or "../" in normalized_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return normalized_path


@router.get('/api/hips/{path:path}')
def get_hips_file(
    normalized_path: Annotated[str, Depends(validate_path)],
):
    try:
        data = hips_file(normalized_path)
    except:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND )
    return Response(
        content=data,
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{os.path.basename(normalized_path)}"',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
        },
    )
