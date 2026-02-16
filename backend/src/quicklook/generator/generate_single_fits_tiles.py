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
from quicklook.datasource import get_datasource
from quicklook.generator.iteratetiles import iterate_tiles
from quicklook.generator.preprocess_ccd import AmpMetadata, ImageStat, PreProcessedCcd, preprocess_ccd
from quicklook.job.job import Job
from quicklook.types import CcdDataRef, CcdName, Progress, ReturnValue, Tile
from quicklook.utils.geom import BBox
from quicklook.utils.imap_unordered_threadpool import imap_unordered_threadpool
from quicklook.utils.timer import Timer

logger = quicklook.mylogging.getLogger(__name__)

ds = get_datasource()

# ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
# ローカルFSからの読み込みは非常に高速なため、制限なしでは全CCDが
# 一度にダウンロードされてtmpディレクトリとメモリを圧迫する。
_download_semaphore_size = config.generator_max_concurrent_ccds_per_job + 2


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
        q = cast(
            queue.Queue[GenerateSingleFitsTilesProgress | CcdMetadata | None],
            manager.Queue(),
        )

        # ダウンロード済み（未処理）のtmpファイル数を制限するセマフォ。
        # download()でacquire → _process_ccd()のunlink後にrelease。
        # Manager経由で作成し、プロセス間で共有可能にする。
        download_sem = manager.Semaphore(_download_semaphore_size)

        # パイプライン各段階のタイムスタンプ記録用
        ccd_timestamps: dict[str, float] = {}  # ccd_name → ccd_generator yield時刻

        def ccd_paths():
            with ThreadPoolExecutor(2) as executor:
                for path in imap_unordered_threadpool(executor, download, timestamped_refs(), max_in_flight=2):
                    yield path

        def timestamped_refs():
            for ref in refs:
                ccd_timestamps[ref.ccd_name] = time.monotonic()
                yield ref

        def download(ref: CcdDataRef):
            t_yield = ccd_timestamps.get(ref.ccd_name, 0.0)
            t0 = time.monotonic()
            download_sem.acquire()
            t_sem = time.monotonic()
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd_name, progress=Progress(4, 1)))
            data_bytes = ds.get_data_sync(ref)
            t_dl = time.monotonic()
            outpath = Path(tmpdir) / f"{ref.ccd_name}_{uuid.uuid4().hex[:8]}.fits"
            outpath.write_bytes(data_bytes)
            logger.info(
                "Downloaded %s (%d bytes) queue_wait=%.3fs sem_wait=%.3fs download=%.3fs total=%.3fs",
                ref.ccd_name, len(data_bytes),
                t0 - t_yield if t_yield > 0 else 0.0,
                t_sem - t0, t_dl - t_sem, t_dl - t_yield if t_yield > 0 else t_dl - t0,
            )
            q.put(GenerateSingleFitsTilesProgress(ccd_name=ref.ccd_name, progress=Progress(4, 2)))
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
                                q,  # type:ignore
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
                q.put(None)  # type: ignore

        with ThreadPoolExecutor(1) as executor:
            fut = executor.submit(main)
            while msg := q.get():
                yield msg
            fut.result()

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
                ccd_name=ppccd.data_ref.ccd_name,
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
            ccd_name=ppccd.data_ref.ccd_name,
            progress=Progress(4, 4),
        )
    )

    args.job.local_storage.fits_header.save(args.ref.ccd_name, ppccd.headers)
    t_end = time.monotonic()

    logger.info(
        "_process_ccd %s: dl_to_pool=%.3fs pool_wait=%.3fs preprocess=%.3fs tiles=%.3fs save=%.3fs total=%.3fs",
        args.ref.ccd_name,
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


if False:
    # これは以前使っていた並列度の低い遅い実装

    import threading

    def generate_single_fits_tiles(
        job: Job,
        ref: CcdDataRef,
    ):
        yield (progress := Progress(total=3))

        data_bytes = ds.get_data_sync(ref)
        yield progress.update()

        try:
            with _bytes_to_file(data_bytes) as path:
                ppccd = preprocess_ccd(ref, path)
                yield progress.update()

            generate_tiles(ppccd, job)
            yield progress.update()

            job.local_storage.fits_header.save(ref, ppccd.headers)

            yield ReturnValue(
                CcdMetadata(
                    ccd_name=ppccd.data_ref.ccd,
                    image_stat=ppccd.stat,
                    amps=ppccd.amps,
                    bbox=ppccd.bbox,
                )
            )
        finally:
            # 遅いgeneratorでこの関数が実行された時
            # coordinatorのcleanupの後にまだこの関数が実行されている可能性がるので
            # ここでもcleanupする。
            #
            # from threading import Timer
            # なぜかPython標準のTimerを使うとgenerator全体が停止してしまう。
            Timer(600, job.local_storage.clear_all).start()

    @contextlib.contextmanager
    def _bytes_to_file(data: bytes, dir=config.fitsio_tmpdir):
        dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dir) as f:
            f.write(data)
            f.flush()
            yield Path(f.name)
