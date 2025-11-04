```python
import boto3
import os
from botocore.client import Config
from botocore.exceptions import ClientError

# 既存のクライアント設定をそのまま利用
s3 = boto3.client(
    's3',
    endpoint_url='https://sdfembs3.sdf.slac.stanford.edu',
    aws_access_key_id=os.environ['QUICKLOOK_s3_tile__access_key'],
    aws_secret_access_key=os.environ['QUICKLOOK_s3_tile__secret_key'],
    config=Config(
        signature_version='s3v4',
        tcp_keepalive=True,
        request_checksum_calculation='when_required',
        response_checksum_validation='when_required',
        s3={'addressing_style': 'path'},
    ),
)

BUCKET = "fov-quicklook-tile"
# 「以下」を対象にするため末尾にスラッシュを付けます
PREFIX = "fov-quicklook/devquicklooks/"

def _chunk(iterable, size=1000):
    """最大1000件ずつに分割"""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

def count_objects_under_prefix(bucket: str, prefix: str) -> int:
    """現在の最新版オブジェクト数を数える（非バージョン単位）。"""
    total = 0
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        total += len(page.get('Contents', []))
    return total

def delete_all_versions_and_markers(bucket: str, prefix: str) -> int:
    """
    バージョニング有効時に、全バージョン＆DeleteMarkersを削除。
    戻り値は削除した version + marker の合計件数。
    """
    deleted = 0
    paginator = s3.get_paginator('list_object_versions')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        to_delete = []
        for v in page.get('Versions', []):
            to_delete.append({'Key': v['Key'], 'VersionId': v['VersionId']})
        for m in page.get('DeleteMarkers', []):
            to_delete.append({'Key': m['Key'], 'VersionId': m['VersionId']})

        for batch in _chunk(to_delete, size=1000):
            if batch:
                s3.delete_objects(Bucket=bucket, Delete={'Objects': batch, 'Quiet': True})
                deleted += len(batch)
    return deleted

def delete_current_objects(bucket: str, prefix: str) -> int:
    """
    現在の最新版（非バージョン単位）のオブジェクトを削除。
    戻り値は削除件数。
    """
    deleted = 0
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        for batch in _chunk(keys, size=1000):
            if batch:
                s3.delete_objects(Bucket=bucket, Delete={'Objects': batch, 'Quiet': True})
                deleted += len(batch)
    return deleted

def delete_prefix(bucket: str, prefix: str, dry_run: bool = False):
    """
    指定プレフィックス配下を完全削除。
      - dry_run=True: 件数のみ表示（削除しない）
      - dry_run=False: 実削除
    """
    # 事前件数（最新版）
    current_count = count_objects_under_prefix(bucket, prefix)
    print(f"[INFO] Target bucket='{bucket}', prefix='{prefix}'")
    print(f"[INFO] Current objects (latest versions) under prefix: {current_count}")

    if dry_run:
        print("[DRY-RUN] No deletion performed.")
        return

    # バージョニング状態確認
    versioning_status = None
    try:
        versioning_status = s3.get_bucket_versioning(Bucket=bucket).get('Status', None)
        print(f"[INFO] Bucket versioning status: {versioning_status}")
    except ClientError as e:
        # 一部のS3互換では未サポートな可能性があるためフォールバック
        print(f"[WARN] get_bucket_versioning failed ({e}); proceeding without version-aware deletion.")

    total_deleted = 0

    # バージョニング対応（EnabledまたはSuspendedならバージョンAPIは使えるケースが多い）
    if versioning_status in ("Enabled", "Suspended"):
        try:
            deleted_versions = delete_all_versions_and_markers(bucket, prefix)
            print(f"[INFO] Deleted versions & delete-markers: {deleted_versions}")
            total_deleted += deleted_versions
        except ClientError as e:
            print(f"[WARN] list_object_versions/delete_objects (versions) failed ({e}); "
                  "falling back to deleting current objects only.")

    # 最新版のオブジェクトも削除（非バージョン or バージョン削除後の残存対策）
    deleted_currents = delete_current_objects(bucket, prefix)
    print(f"[INFO] Deleted current objects: {deleted_currents}")
    total_deleted += deleted_currents

    # 後確認
    remaining = count_objects_under_prefix(bucket, prefix)
    print(f"[INFO] Total deleted (count of ops): {total_deleted}")
    print(f"[INFO] Remaining current objects under prefix: {remaining}")

# まずはドライランで対象件数を確認
delete_prefix(BUCKET, PREFIX, dry_run=False)

# 問題なければ本番削除
# delete_prefix(BUCKET, PREFIX, dry_run=False)
```
