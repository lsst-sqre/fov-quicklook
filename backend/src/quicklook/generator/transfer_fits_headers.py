"""Transfer FITS headers to object storage."""

import logging
import pickle

from quicklook.comm.generator import self_generator_id
from quicklook.job.job import Job
from quicklook.types import CcdName, CcdDataRef, Progress

logger = logging.getLogger(__name__)


def transfer_fits_headers(job: Job):
    """
    ローカルストレージに保存されたFITS headerをobject storageにアップロードする。
    自ノードで処理したCCDのheaderのみをアップロードする。
    """
    # 自ノードが処理したCCDのリストを取得
    ccd_names = _iter_primary_ccd_names(job)
    ccd_names_list = list(ccd_names)

    uploaded_size = 0
    for ccd_name in ccd_names_list:
        ref = CcdDataRef(visit=job.visit, ccd=ccd_name)

        # ローカルストレージからheaderを読み込む
        headers = job.local_storage.fits_header.load(ref.ccd_name)

        # object storageにアップロード
        size = job.object_storage.put_fits_headers_sync(ccd_name, headers)
        uploaded_size += size

    return uploaded_size


def _iter_primary_ccd_names(job: Job):
    """自ノードが処理したCCDのリストを取得"""
    dist_config = job.local_storage.ccd_distribution_config.load()
    my_generator_id = self_generator_id()

    for ccd_name, generator_id in dist_config.ccd_generator_map.items():
        if generator_id == my_generator_id:
            yield ccd_name
