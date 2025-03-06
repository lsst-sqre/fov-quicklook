import io
import minio


def download_object_from_s3(
    client: minio.Minio,
    bucket: str,
    key: str,
    *,
    offset: int = 0,
    length: int = 0,
) -> bytes:
    response = None
    try:
        response = client.get_object(
            bucket,
            key,
            offset=offset,
            length=length,
        )
        return response.read()

    finally:
        if response:  # pragma: no branch
            response.close()
            response.release_conn()


def upload_object_to_s3(
    client: minio.Minio,
    bucket: str,
    key: str,
    data: bytes,
    content_type: str,
) -> None:
    data_buf = io.BytesIO(data)
    client.put_object(
        bucket,
        key,
        data_buf,
        len(data),
        content_type=content_type,
    )
