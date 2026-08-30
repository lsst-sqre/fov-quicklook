import contextlib
import gc
import multiprocessing
import queue
import tempfile
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Generator, Iterable, cast

import quicklook.mylogging
from quicklook.comm.generator import GeneratorIdInitializer
from quicklook.config import config
from quicklook.generator.ccd_download import AdaptiveDownloadTimeout, download_ccd_to_path
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat, PreProcessedCcd, preprocess_ccd
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue, Tile
from quicklook.utils.geom import BBox
from quicklook.utils.imap_unordered_threadpool import imap_unordered_threadpool
from quicklook.utils.timer import Timer
from quicklook.utils.wcs import FitsWcsHeader

logger = quicklook.mylogging.getLogger(__name__)

# ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
# ローカルFSからの読み込みは非常に高速なため、制限なしでは全CCDが
# 一度にダウンロードされてtmpディレクトリとメモリを圧迫する。
_download_semaphore_size = config.generator_max_concurrent_ccds_per_job + 2
_QUEUE_DONE = object()


@dataclass
class GenerateSingleFitsTilesProgress:
    ccd_name: CcdName
    progress: Progress


@dataclass
class CcdMetadata:
    ccd_name: CcdName
    image_stat: ImageStat
    amps: list[AmpMetadata]
    bbox: BBox
    wcs: FitsWcsHeader | None = None


def _initialize_pool_worker(initializers: list[Callable[[], ContextManager]]) -> None:
    """multiprocessing.Pool用のワーカー初期化関数"""
    global _pool_exit_stack
    _pool_exit_stack = ExitStack()
    for init in initializers:
        _pool_exit_stack.enter_context(init())


_pool_exit_stack: ExitStack | None = None


def generate_single_fits_tiles_pipeline(
    job: Job,
    refs: Iterable[CcdDataRef],
) -> Generator[GenerateSingleFitsTilesProgress | CcdMetadata]:
    with tempfile.TemporaryDirectory() as tmpdir, multiprocessing.Manager() as manager:
        q: queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata | object] = queue.Queue()
        progress_queue = cast(
            queue.Queue[GenerateSingleFitsTilesProgress | None],
            manager.Queue(),
        )

        # ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
        # download()でacquire → _process_ccd()のunlink後にrelease。
        # Manager経由で作成し、プロセス間で共有可能にする。
        download_sem = manager.Semaphore(_download_semaphore_size)
        # refs is a live stream from the coordinator. Materializing it here would
        # block until the coordinator sends the terminal sentinel, which only
        # happens after CCD processing completes.
        adaptive_timeout = AdaptiveDownloadTimeout(
            sample_target=max((config.generator_max_concurrent_ccds_per_job + 1) // 2, 1)
        )

        # パイプライン各段階のタイムスタンプ記録用
        ccd_timestamps: dict[str, float] = {}  # ccd_name → ccd_generator yield時刻

        def ccd_paths():
            with ThreadPoolExecutor(8) as executor:
                for path in imap_unordered_threadpool(executor, download, timestamped_refs(), max_in_flight=8):
                    yield path

        def timestamped_refs():
            for ref in refs:
                ccd_timestamps[ref.ccd] = time.monotonic()
                yield ref

        def download(ref: CcdDataRef):
            t_yield = ccd_timestamps.get(ref.ccd, 0.0)
            t0 = time.monotonic()
            download_sem.acquire()
            t_sem = time.monotonic()
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd, progress=Progress(4, 1)))
            outpath = Path(tmpdir) / f"{ref.ccd}_{uuid.uuid4().hex[:8]}.fits"
            download_result = download_ccd_to_path(
                ref,
                outpath,
                timeout=adaptive_timeout,
            )
            t_dl = download_result.download_done_time
            logger.info(
                "Downloaded %s (%d bytes) queue_wait=%.3fs sem_wait=%.3fs download=%.3fs total=%.3fs",
                ref.ccd, download_result.bytes_written,
                t0 - t_yield if t_yield > 0 else 0.0,
                t_sem - t0,
                download_result.elapsed,
                t_dl - t_yield if t_yield > 0 else t_dl - t0,
            )
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd, progress=Progress(4, 2)))
            return (ref, outpath, t_dl)

        def main():
            ccd_count = 0
            try:
                initializers = [GeneratorIdInitializer()]
                with multiprocessing.Pool(
                    config.generator_max_concurrent_ccds_per_job,
                    initializer=_initialize_pool_worker,
                    initargs=(initializers,),
                    maxtasksperchild=1,
                ) as pool:
                    for ccd_metadata in pool.imap_unordered(
                        _process_ccd,
                        (
                            ProcessCcdArgs(
                                job,
                                ref,
                                path,
                                progress_queue,  # type:ignore
                                download_sem,
                                pool_submit_time=time.monotonic(),
                                download_done_time=dl_done_time,
                            )
                            for ref, path, dl_done_time in ccd_paths()
                        ),
                    ):
                        q.put(ccd_metadata)
                        ccd_count += 1
                        logger.info(f"CcdMetadata queued in main: {ccd_metadata.ccd_name} ({ccd_count})")
            except Exception as e:
                logger.error(f"main() error after {ccd_count} CCDs: {e}")
                raise
            finally:
                logger.info(f"main() finished, total CcdMetadata queued: {ccd_count}")
                progress_queue.put(None)  # type: ignore
                q.put(_QUEUE_DONE)

        def drain_progress_queue():
            while True:
                msg = progress_queue.get()
                if msg is None:
                    break
                q.put(msg)
            q.put(_QUEUE_DONE)

        with ThreadPoolExecutor(2) as executor:
            fut = executor.submit(main)
            progress_fut = executor.submit(drain_progress_queue)
            done_count = 0
            while done_count < 2:
                msg = q.get()
                if msg is _QUEUE_DONE:
                    done_count += 1
                    continue
                yield cast(GenerateSingleFitsTilesProgress | CcdMetadata, msg)
            fut.result()
            progress_fut.result()

    gc.collect()


@dataclass
class ProcessCcdArgs:
    job: Job
    ref: CcdDataRef
    path: Path
    progress: queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata]
    download_sem: Any  # multiprocessing.Manager().Semaphore() proxy
    pool_submit_time: float = 0.0  # Pool投入時の monotonic 時刻
    download_done_time: float = 0.0  # ダウンロード完了時の monotonic 時刻


def _process_ccd(args: ProcessCcdArgs):
    t_start = time.monotonic()
    pool_wait = t_start - args.pool_submit_time if args.pool_submit_time > 0 else 0.0
    dl_to_pool = args.pool_submit_time - args.download_done_time if args.download_done_time > 0 and args.pool_submit_time > 0 else 0.0
    try:
        ppccd = preprocess_ccd(args.ref, args.path)
        t_preprocess = time.monotonic()
        args.progress.put(
            GenerateSingleFitsTilesProgress(
                ccd_name=ppccd.data_ref.ccd,
                progress=Progress(4, 3),
            )
        )
    finally:
        args.path.unlink(missing_ok=True)
        args.download_sem.release()

    generate_tiles(ppccd, args.job)
    t_tiles = time.monotonic()
    args.progress.put(
        GenerateSingleFitsTilesProgress(
            ccd_name=ppccd.data_ref.ccd,
            progress=Progress(4, 4),
        )
    )

    args.job.local_storage.fits_header.save(args.ref.ccd, ppccd.headers)
    t_end = time.monotonic()

    logger.info(
        "_process_ccd %s: dl_to_pool=%.3fs pool_wait=%.3fs preprocess=%.3fs tiles=%.3fs save=%.3fs total=%.3fs",
        args.ref.ccd,
        dl_to_pool,
        pool_wait,
        t_preprocess - t_start,
        t_tiles - t_preprocess,
        t_end - t_tiles,
        t_end - t_start,
    )

    # CcdMetadata を return して main() 側で q.put する。
    # ワーカープロセスから Manager Queue proxy 経由で直接 put すると、
    # Pool の結果パイプとの間でレース条件が発生し、
    # main() の q.put(None) が CcdMetadata より先に到着することがある。
    ccd_metadata = CcdMetadata(
        ccd_name=ppccd.data_ref.ccd,
        image_stat=ppccd.stat,
        amps=ppccd.amps,
        bbox=ppccd.bbox,
        wcs=ppccd.wcs,
    )
    return ccd_metadata


def generate_tiles(
    ppccd: PreProcessedCcd,
    job: Job,
):
    storage = job.local_storage

    def cb(tile: Tile):
        storage.single_fits_tile.save(ppccd.data_ref.ccd, tile)

    iterate_tiles(ppccd, cb)
