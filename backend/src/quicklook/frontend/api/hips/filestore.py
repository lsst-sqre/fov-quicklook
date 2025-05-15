import pathlib
import threading
from dataclasses import dataclass
from functools import cache
from typing import Any, Iterable

from quicklook.utils.ttlcache import ttlcache


@ttlcache(ttl=60)
def hips_repositories() -> Iterable[str]:
    for reponame in _list_entries('LSSTCam/hips/template/DRP/20250420_20250429/w_2025_18/DM-50628/'):
        for color in _list_entries(f'LSSTCam/hips/template/DRP/20250420_20250429/w_2025_18/DM-50628/{reponame}/'):
            yield f'{reponame}/{color}'


def hips_file(path: str) -> bytes:
    full_path = f"LSSTCam/hips/template/DRP/20250420_20250429/w_2025_18/DM-50628/{path}"
    return _get_object(full_path)


def _list_entries(path: str) -> list[str]:
    ctx = _s3_context()
    response = ctx.client.list_objects_v2(Bucket=ctx.bucket, Prefix=path, Delimiter='/')
    entries: list[str] = []

    # Add subdirectories (CommonPrefixes)
    if 'CommonPrefixes' in response:
        for prefix in response['CommonPrefixes']:
            # Extract only the directory name from the prefix
            prefix_path = prefix['Prefix']
            if prefix_path.endswith('/'):
                prefix_path = prefix_path[:-1]
            entries.append(pathlib.Path(prefix_path).name)

    # Add files (Contents)
    if 'Contents' in response:
        for obj in response['Contents']:
            # Skip the directory entry itself
            if obj['Key'] != path and obj['Key'] != f"{path}/":
                entries.append(pathlib.Path(obj['Key']).name)

    return entries


def _get_object(path: str) -> bytes:
    ctx = _s3_context()
    response = ctx.client.get_object(Bucket=ctx.bucket, Key=path)
    return response['Body'].read()


@dataclass
class S3Context:
    client: Any
    bucket: str


def _s3_context() -> S3Context:
    thread_id = threading.get_ident()
    return _s3_context_thread_local(thread_id)


@cache
def _s3_context_thread_local(thread_id: int) -> S3Context:
    from lsst.daf.butler import Butler
    from lsst.resources.s3 import S3ResourcePath

    from quicklook.butlerutils import chown_pgpassfile

    chown_pgpassfile()

    b = Butler("embargo")  # type: ignore
    p = b.get_datastore_roots()['FileDatastore@<butlerRoot>']
    if not isinstance(p, S3ResourcePath):
        raise ValueError("The datastore root is not an S3 path.")
    return S3Context(client=p.client, bucket=p._bucket)  # type: ignore
