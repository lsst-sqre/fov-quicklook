import os
import tempfile
from typing import Callable

os.environ['http_proxy'] = ''

from pathlib import Path

import boto3
import numpy
from botocore.client import Config

# MinIOのエンドポイント、アクセスキー、シークレットキーを設定
minio_url = "http://192.168.13.201:9000"
access_key = "quicklook"
secret_key = "password"


s3 = boto3.client(
    's3',
    endpoint_url=minio_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version='s3v4'),
)


def main():
    # boto3のS3クライアントを作成

    bucket = 'quicklook-tile'
    key = 'sample'
    body = numpy.random.bytes(32 * (1 << 20))

    def put_object():
        s3.put_object(Bucket=bucket, Key=key, Body=body)
        # multipart_upload_bytes(bucket, key, body)
        # upload_bytes_to_s3(bucket, key, body)

    timeit("put_object", put_object, 10)

    # obj = s3.get_object(Bucket=bucket, Key=Path(__file__).name)
    # print(obj['Body'].read())


def timeit(label: str, f: Callable, iteration=1):
    import time

    start = time.time()
    for _ in range(iteration):
        print(f"iteration {_}")
        f()
    end = time.time()
    print(f"{label}: {end - start:.3f} sec")


import boto3


def multipart_upload_bytes(bucket_name: str, object_name: str, data: bytes, part_size: int = 5 * 1024 * 1024):
    # マルチパートアップロードの初期化
    response = s3.create_multipart_upload(Bucket=bucket_name, Key=object_name)
    upload_id = response['UploadId']

    try:
        # データをパートに分割してアップロード
        parts = []
        for i in range(0, len(data), part_size):
            part_number = len(parts) + 1
            part_data = data[i : i + part_size]

            response = s3.upload_part(Bucket=bucket_name, Key=object_name, PartNumber=part_number, UploadId=upload_id, Body=part_data)
            parts.append({'PartNumber': part_number, 'ETag': response['ETag']})

        # アップロードを完了
        s3.complete_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id, MultipartUpload={'Parts': parts})
        print(f"Upload completed for {object_name} in {bucket_name}.")

    except Exception as e:
        s3.abort_multipart_upload(Bucket=bucket_name, Key=object_name, UploadId=upload_id)
        print(f"Upload failed: {e}")
        raise


def upload_bytes_to_s3(bucket_name: str, object_name: str, data: bytes):
    # /dev/shm にテンポラリファイルを作成
    with tempfile.NamedTemporaryFile(dir='/dev/shm', delete=False) as tmp_file:
        try:
            # データを書き込む
            tmp_file.write(data)
            tmp_file_path = tmp_file.name

        except Exception as e:
            os.remove(tmp_file.name)
            raise e

    try:
        # ファイルをS3にアップロード
        s3.upload_file(tmp_file_path, bucket_name, object_name)
        print(f"Upload completed for {object_name} in {bucket_name}.")

    finally:
        # テンポラリファイルを削除
        os.remove(tmp_file_path)


main()
